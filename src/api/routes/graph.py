"""Knowledge Graph API — Obsidian-like relational view. Always FREE."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.db.models import Tenant

router = APIRouter()


@router.get("/graph")
async def get_knowledge_graph(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(200, ge=1, le=500),
):
    """Get the full knowledge graph — nodes (entities) and edges (relationships).

    Returns data ready for visualization (Cytoscape.js, D3, etc.)
    Always FREE — 0 credits.
    """
    # Get entities grouped by type with document connections
    entities_result = await session.execute(
        text("""
            SELECT
                e.id::text,
                e.entity_type,
                e.value,
                e.normalized_value,
                e.confidence,
                e.document_id::text,
                d.filename as document_name,
                d.doc_type as document_type
            FROM entities e
            JOIN documents d ON d.id = e.document_id
            WHERE e.tenant_id = :tenant_id
            ORDER BY e.entity_type, e.value
            LIMIT :limit
        """),
        {"tenant_id": str(tenant.id), "limit": limit},
    )
    entities = entities_result.mappings().all()

    # Build nodes: unique entities + documents
    nodes = []
    node_ids = set()

    # Add document nodes
    doc_nodes = {}
    for e in entities:
        doc_id = e["document_id"]
        if doc_id not in doc_nodes:
            doc_nodes[doc_id] = {
                "id": doc_id,
                "label": e["document_name"],
                "type": "document",
                "subtype": e["document_type"] or "other",
                "size": 1,
            }
        else:
            doc_nodes[doc_id]["size"] += 1

    nodes.extend(doc_nodes.values())
    node_ids.update(doc_nodes.keys())

    # Add entity nodes (deduplicated by value+type)
    entity_key_to_id = {}
    for e in entities:
        key = f"{e['entity_type']}:{e['value'].lower()}"
        if key not in entity_key_to_id:
            entity_key_to_id[key] = e["id"]
            nodes.append({
                "id": e["id"],
                "label": e["value"],
                "type": "entity",
                "subtype": e["entity_type"],
                "size": 1,
            })
            node_ids.add(e["id"])
        else:
            # Increment size for duplicate entities
            for n in nodes:
                if n["id"] == entity_key_to_id[key]:
                    n["size"] += 1
                    break

    # Build edges: entity -> document connections
    edges = []
    for e in entities:
        key = f"{e['entity_type']}:{e['value'].lower()}"
        entity_id = entity_key_to_id.get(key, e["id"])
        edges.append({
            "source": entity_id,
            "target": e["document_id"],
            "type": "mentioned_in",
            "label": "mentioned in",
        })

    # Find entities that appear in multiple documents (cross-doc connections)
    multi_doc_result = await session.execute(
        text("""
            SELECT value, entity_type, array_agg(DISTINCT document_id::text) as doc_ids
            FROM entities
            WHERE tenant_id = :tenant_id
            GROUP BY value, entity_type
            HAVING count(DISTINCT document_id) > 1
        """),
        {"tenant_id": str(tenant.id)},
    )
    cross_doc = multi_doc_result.mappings().all()

    # Stats
    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "entity_count": len([n for n in nodes if n["type"] == "entity"]),
        "document_count": len([n for n in nodes if n["type"] == "document"]),
        "cross_document_entities": len(cross_doc),
    }

    # Entity type breakdown
    type_counts = {}
    for n in nodes:
        if n["type"] == "entity":
            type_counts[n["subtype"]] = type_counts.get(n["subtype"], 0) + 1
    stats["entity_types"] = type_counts

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
        "cross_document_connections": [
            {
                "entity": r["value"],
                "type": r["entity_type"],
                "document_count": len(r["doc_ids"]),
                "documents": r["doc_ids"],
            }
            for r in cross_doc
        ],
    }


@router.get("/graph/entity/{entity_value}")
async def get_entity_connections(
    entity_value: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get all documents and related entities for a specific entity."""
    result = await session.execute(
        text("""
            SELECT e.*, d.filename, d.doc_type, d.summary
            FROM entities e
            JOIN documents d ON d.id = e.document_id
            WHERE e.tenant_id = :tenant_id
            AND LOWER(e.value) = LOWER(:value)
        """),
        {"tenant_id": str(tenant.id), "value": entity_value},
    )
    mentions = result.mappings().all()

    # Get co-occurring entities in the same documents
    if mentions:
        doc_ids = list(set(str(m["document_id"]) for m in mentions))
        co_result = await session.execute(
            text("""
                SELECT DISTINCT value, entity_type, count(*) as frequency
                FROM entities
                WHERE tenant_id = :tenant_id
                AND document_id::text = ANY(:doc_ids)
                AND LOWER(value) != LOWER(:value)
                GROUP BY value, entity_type
                ORDER BY frequency DESC
                LIMIT 20
            """),
            {"tenant_id": str(tenant.id), "doc_ids": doc_ids, "value": entity_value},
        )
        related = co_result.mappings().all()
    else:
        related = []

    return {
        "entity": entity_value,
        "mention_count": len(mentions),
        "documents": [
            {
                "id": str(m["document_id"]),
                "filename": m["filename"],
                "doc_type": m["doc_type"],
                "summary": m["summary"],
            }
            for m in mentions
        ],
        "related_entities": [
            {"value": r["value"], "type": r["entity_type"], "frequency": r["frequency"]}
            for r in related
        ],
    }
