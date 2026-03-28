"""Document Analysis Agent — LangGraph state machine.

This is the core agentic component. When a document is uploaded, this agent:
1. Extracts text
2. Classifies the document (with confidence-based retry)
3. Extracts entities
4. Resolves entities against the existing knowledge graph
5. Finds cross-document connections
6. Detects contradictions with related documents
7. Assesses compliance
8. Persists everything and emits events

This replaces the linear pipeline in src/enrichment/pipeline.py with
an intelligent, self-correcting agent that reasons about how the new
document fits into the existing document ecosystem.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# STATE DEFINITION
# =============================================================================


class DocumentAnalysisState(TypedDict):
    """State accumulated as the agent processes a document."""

    # Input
    document_id: str
    tenant_id: str
    tier: str  # "light", "standard", "deep"

    # Text
    text_content: str
    filename: str
    mime_type: str

    # Classification
    classification: dict | None
    doc_type: str
    classification_confidence: float

    # Entities
    entities: list[dict]
    relationships: list[dict]
    resolved_entity_ids: list[str]

    # Cross-document intelligence
    cross_doc_matches: list[dict]
    contradictions: list[dict]
    compliance_findings: list[dict]

    # Agent reasoning
    reasoning_chain: list[str]
    retry_count: int
    credits_consumed: float

    # Output
    status: str
    error: str | None


# =============================================================================
# NODE FUNCTIONS
# =============================================================================


async def extract_text_node(state: DocumentAnalysisState) -> dict:
    """Extract text from the document file."""
    from src.enrichment.text_extract import extract_text

    # For now, text_content is passed in from the upload handler
    # In production, this would fetch from S3/storage
    text = state.get("text_content", "")
    if not text:
        return {
            "status": "error",
            "error": "No text content available",
            "reasoning_chain": state.get("reasoning_chain", [])
            + ["extract_text: No text content found"],
        }

    return {
        "text_content": text,
        "reasoning_chain": state.get("reasoning_chain", [])
        + [f"extract_text: Extracted {len(text)} chars"],
    }


async def classify_node(state: DocumentAnalysisState) -> dict:
    """Classify the document using LLM (Haiku for speed)."""
    from src.enrichment.processor import ClaudeProvider

    llm = ClaudeProvider()
    text = state["text_content"]

    # Use smaller context on first try, larger on retry
    max_chars = 8000 if state.get("retry_count", 0) == 0 else 16000

    classification = await llm.classify(text[:max_chars])

    doc_type = classification.get("doc_type", "other")
    confidence = classification.get("confidence", 0.0)

    return {
        "classification": classification,
        "doc_type": doc_type,
        "classification_confidence": confidence,
        "credits_consumed": state.get("credits_consumed", 0) + settings.credit_cost_classify,
        "reasoning_chain": state.get("reasoning_chain", [])
        + [f"classify: {doc_type} (confidence={confidence:.2f}, chars={max_chars})"],
    }


async def extract_entities_node(state: DocumentAnalysisState) -> dict:
    """Extract entities and relationships using LLM (Sonnet for accuracy)."""
    from src.enrichment.processor import ClaudeProvider

    llm = ClaudeProvider()
    result = await llm.extract_entities(state["text_content"])

    entities = result.get("entities", [])
    relationships = result.get("relationships", [])

    return {
        "entities": entities,
        "relationships": relationships,
        "credits_consumed": state.get("credits_consumed", 0) + settings.credit_cost_extract,
        "reasoning_chain": state.get("reasoning_chain", [])
        + [f"extract_entities: Found {len(entities)} entities, {len(relationships)} relationships"],
    }


async def resolve_entities_node(state: DocumentAnalysisState) -> dict:
    """Resolve extracted entities against the existing knowledge graph."""
    from src.agents.tools.document_tools import generate_embedding
    from src.graph.resolution import EntityResolver
    from src.db.base import async_session

    resolved_ids = []
    resolution_summary = []

    async with async_session() as session:
        resolver = EntityResolver(session, uuid.UUID(state["tenant_id"]))

        for entity_data in state.get("entities", []):
            entity_value = entity_data.get("value", "")
            entity_type = entity_data.get("entity_type", "other")

            if not entity_value:
                continue

            # Generate embedding for similarity matching
            try:
                embedding = await generate_embedding(entity_value)
            except Exception:
                embedding = None

            resolved, resolution_type = await resolver.resolve(
                entity_value, entity_type, embedding
            )
            resolved_ids.append(str(resolved.id))
            resolution_summary.append(f"{entity_value} → {resolution_type}")

        await session.commit()

    return {
        "resolved_entity_ids": resolved_ids,
        "reasoning_chain": state.get("reasoning_chain", [])
        + [
            f"resolve_entities: {resolver.stats['exact_matches']} exact, "
            f"{resolver.stats['embedding_matches']} embedding, "
            f"{resolver.stats['ambiguous']} ambiguous, "
            f"{resolver.stats['new_entities']} new"
        ],
    }


async def find_cross_doc_node(state: DocumentAnalysisState) -> dict:
    """Find documents that share entities with this document."""
    from src.agents.tools.document_tools import find_cross_doc_matches
    from src.db.base import async_session

    async with async_session() as session:
        matches = await find_cross_doc_matches(
            session,
            uuid.UUID(state["tenant_id"]),
            uuid.UUID(state["document_id"]),
        )

    return {
        "cross_doc_matches": matches,
        "reasoning_chain": state.get("reasoning_chain", [])
        + [f"find_cross_doc: Found {len(matches)} related documents via shared entities"],
    }


async def detect_contradictions_node(state: DocumentAnalysisState) -> dict:
    """Compare this document against related documents for contradictions."""
    from src.enrichment.processor import ClaudeProvider
    from src.db.base import async_session
    from src.db.models import Document

    if not state.get("cross_doc_matches"):
        return {
            "contradictions": [],
            "reasoning_chain": state.get("reasoning_chain", [])
            + ["detect_contradictions: No cross-doc matches, skipping"],
        }

    llm = ClaudeProvider()
    all_contradictions = []

    async with async_session() as session:
        # Only check top 3 most connected documents to limit API calls
        for match in state["cross_doc_matches"][:3]:
            other_doc = await session.get(Document, uuid.UUID(match["document_id"]))
            if not other_doc or not other_doc.text_content:
                continue

            try:
                from src.agents.tools.document_tools import detect_contradictions

                contradictions = await detect_contradictions(
                    llm,
                    state["text_content"],
                    other_doc.text_content,
                    state.get("filename", "Current Document"),
                    other_doc.filename,
                    match.get("shared_entities", []),
                )

                for c in contradictions:
                    c["other_document_id"] = match["document_id"]
                    c["other_document_name"] = match["filename"]
                    all_contradictions.append(c)

            except Exception as e:
                logger.warning(f"Contradiction check failed: {e}")

    credits = settings.credit_cost_extract * len(state["cross_doc_matches"][:3])

    return {
        "contradictions": all_contradictions,
        "credits_consumed": state.get("credits_consumed", 0) + credits,
        "reasoning_chain": state.get("reasoning_chain", [])
        + [f"detect_contradictions: Found {len(all_contradictions)} contradictions across {len(state['cross_doc_matches'][:3])} docs"],
    }


async def assess_compliance_node(state: DocumentAnalysisState) -> dict:
    """Apply compliance rules based on document type and extracted data."""
    from src.agents.tools.document_tools import assess_compliance

    findings = await assess_compliance(
        state.get("doc_type", "other"),
        state.get("classification", {}),
        state.get("entities", []),
    )

    return {
        "compliance_findings": findings,
        "reasoning_chain": state.get("reasoning_chain", [])
        + [f"assess_compliance: {len(findings)} findings for {state.get('doc_type', 'other')}"],
    }


async def persist_results_node(state: DocumentAnalysisState) -> dict:
    """Persist all results to the database in a single transaction."""
    from src.db.base import async_session
    from src.db.models import Document, Entity, CreditTransaction
    from sqlalchemy import text as sql_text

    async with async_session() as session:
        doc = await session.get(Document, uuid.UUID(state["document_id"]))
        if not doc:
            return {"status": "error", "error": "Document not found"}

        # Update document with classification
        classification = state.get("classification", {})
        doc.doc_type = state.get("doc_type", "other")
        doc.classification_confidence = state.get("classification_confidence", 0.0)
        doc.summary = classification.get("summary")
        doc.language = classification.get("language", "en")
        doc.prompt_version = classification.get("prompt_version")
        doc.enrichment_tier = state.get("tier", "standard")
        doc.enrichment_metadata = {
            "agent": "document_analysis",
            "reasoning_chain": state.get("reasoning_chain", []),
            "entity_count": len(state.get("entities", [])),
            "relationship_count": len(state.get("relationships", [])),
            "cross_doc_count": len(state.get("cross_doc_matches", [])),
            "contradiction_count": len(state.get("contradictions", [])),
            "compliance_finding_count": len(state.get("compliance_findings", [])),
        }

        # Compliance dates
        if classification.get("expiry_date"):
            try:
                doc.expiry_date = datetime.fromisoformat(classification["expiry_date"])
            except (ValueError, TypeError):
                pass
        if classification.get("review_due_date"):
            try:
                doc.review_due_date = datetime.fromisoformat(classification["review_due_date"])
            except (ValueError, TypeError):
                pass

        doc.compliance_tags = classification.get("compliance_frameworks", [])

        # Update text search index
        if state.get("text_content"):
            await session.execute(
                sql_text(
                    "UPDATE documents SET text_search = to_tsvector('english', :content) "
                    "WHERE id = :doc_id"
                ),
                {"content": state["text_content"][:100000], "doc_id": state["document_id"]},
            )

        # Generate and store embedding
        try:
            from src.agents.tools.document_tools import generate_embedding

            embedding = await generate_embedding(
                state["text_content"], classification.get("summary", "")
            )
            await session.execute(
                sql_text("UPDATE documents SET embedding = :emb WHERE id = :id"),
                {"emb": str(embedding), "id": state["document_id"]},
            )
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")

        # Save entities
        for i, entity_data in enumerate(state.get("entities", [])):
            resolved_id = None
            if i < len(state.get("resolved_entity_ids", [])):
                resolved_id = uuid.UUID(state["resolved_entity_ids"][i])

            entity = Entity(
                tenant_id=uuid.UUID(state["tenant_id"]),
                document_id=uuid.UUID(state["document_id"]),
                entity_type=entity_data.get("entity_type", "other"),
                value=entity_data.get("value", ""),
                normalized_value=entity_data.get("normalized_value"),
                confidence=entity_data.get("confidence", 1.0),
                resolved_entity_id=resolved_id,
                extra_data={"context": entity_data.get("context")},
            )
            session.add(entity)

        # Log credit transaction
        txn = CreditTransaction(
            tenant_id=uuid.UUID(state["tenant_id"]),
            action="agent_enrichment",
            credits=state.get("credits_consumed", 0),
            document_id=uuid.UUID(state["document_id"]),
            extra_data={
                "agent": "document_analysis",
                "tier": state.get("tier"),
            },
        )
        session.add(txn)

        # Update tenant credits
        await session.execute(
            sql_text(
                "UPDATE tenants SET credits_used_this_period = credits_used_this_period + :credits "
                "WHERE id = :tenant_id"
            ),
            {"credits": state.get("credits_consumed", 0), "tenant_id": state["tenant_id"]},
        )

        # Create alerts for contradictions
        from src.agents.tools.document_tools import create_persistent_alert

        for contradiction in state.get("contradictions", []):
            await create_persistent_alert(
                session,
                uuid.UUID(state["tenant_id"]),
                alert_type="contradiction",
                severity=contradiction.get("severity", "warning"),
                title=f"Contradiction: {contradiction.get('field', 'unknown')}",
                message=f"{state.get('filename', 'Document')} says '{contradiction.get('value_a', '')}' "
                f"but {contradiction.get('other_document_name', 'another document')} says "
                f"'{contradiction.get('value_b', '')}'",
                details=contradiction,
                document_ids=[uuid.UUID(state["document_id"])],
            )

        # Create alerts for compliance findings
        for finding in state.get("compliance_findings", []):
            if finding.get("severity") in ("critical", "warning"):
                await create_persistent_alert(
                    session,
                    uuid.UUID(state["tenant_id"]),
                    alert_type=finding.get("type", "compliance"),
                    severity=finding["severity"],
                    title=finding.get("message", "Compliance finding"),
                    message=f"Framework: {finding.get('framework', 'general')}",
                    details=finding,
                    document_ids=[uuid.UUID(state["document_id"])],
                )

        doc.status = "enriched"
        await session.commit()

    return {
        "status": "enriched",
        "reasoning_chain": state.get("reasoning_chain", [])
        + [f"persist_results: Saved {len(state.get('entities', []))} entities, "
           f"{len(state.get('contradictions', []))} contradictions, "
           f"{len(state.get('compliance_findings', []))} compliance findings"],
    }


async def emit_events_node(state: DocumentAnalysisState) -> dict:
    """Emit events for downstream processing."""
    from src.events.bus import event_bus

    await event_bus.emit("document.enriched", {
        "document_id": state["document_id"],
        "tenant_id": state["tenant_id"],
        "doc_type": state.get("doc_type"),
        "entity_count": len(state.get("entities", [])),
        "cross_doc_count": len(state.get("cross_doc_matches", [])),
        "contradiction_count": len(state.get("contradictions", [])),
        "credits_consumed": state.get("credits_consumed", 0),
    })

    return {
        "reasoning_chain": state.get("reasoning_chain", [])
        + ["emit_events: document.enriched event emitted"],
    }


# =============================================================================
# CONDITIONAL EDGES
# =============================================================================


def quality_gate(state: DocumentAnalysisState) -> str:
    """Route based on classification confidence."""
    confidence = state.get("classification_confidence", 0)
    retry_count = state.get("retry_count", 0)

    if confidence < settings.confidence_threshold and retry_count < 2:
        return "reclassify"
    return "continue"


def tier_gate(state: DocumentAnalysisState) -> str:
    """Route based on enrichment tier."""
    tier = state.get("tier", "standard")
    if tier == "light":
        return "skip_extraction"
    return "extract"


def deep_gate(state: DocumentAnalysisState) -> str:
    """Route based on whether cross-doc analysis should run."""
    tier = state.get("tier", "standard")
    cross_docs = state.get("cross_doc_matches", [])

    if tier == "deep" and cross_docs:
        return "check_contradictions"
    return "skip_contradictions"


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================


def build_document_analysis_graph() -> StateGraph:
    """Build the LangGraph state machine for document analysis."""
    graph = StateGraph(DocumentAnalysisState)

    # Add nodes
    graph.add_node("extract_text", extract_text_node)
    graph.add_node("classify", classify_node)
    graph.add_node("reclassify", reclassify_node)
    graph.add_node("extract_entities", extract_entities_node)
    graph.add_node("resolve_entities", resolve_entities_node)
    graph.add_node("find_cross_doc", find_cross_doc_node)
    graph.add_node("detect_contradictions", detect_contradictions_node)
    graph.add_node("assess_compliance", assess_compliance_node)
    graph.add_node("persist_results", persist_results_node)
    graph.add_node("emit_events", emit_events_node)

    # Set entry point
    graph.set_entry_point("extract_text")

    # Edges
    graph.add_edge("extract_text", "classify")

    # Quality gate: retry if confidence is low
    graph.add_conditional_edges("classify", quality_gate, {
        "reclassify": "reclassify",
        "continue": "extract_entities",
    })
    graph.add_conditional_edges("reclassify", quality_gate, {
        "reclassify": "extract_entities",  # Max 2 retries, then move on
        "continue": "extract_entities",
    })

    # Entity extraction → resolution → cross-doc → contradictions
    graph.add_edge("extract_entities", "resolve_entities")
    graph.add_edge("resolve_entities", "find_cross_doc")

    # Deep gate: check contradictions only for deep tier with cross-doc matches
    graph.add_conditional_edges("find_cross_doc", deep_gate, {
        "check_contradictions": "detect_contradictions",
        "skip_contradictions": "assess_compliance",
    })
    graph.add_edge("detect_contradictions", "assess_compliance")

    # Finalize
    graph.add_edge("assess_compliance", "persist_results")
    graph.add_edge("persist_results", "emit_events")
    graph.add_edge("emit_events", END)

    return graph


async def reclassify_node(state: DocumentAnalysisState) -> dict:
    """Retry classification with larger context and reflection."""
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "reasoning_chain": state.get("reasoning_chain", [])
        + [f"reclassify: Retrying with larger context (attempt {state.get('retry_count', 0) + 1})"],
        **(await classify_node(state)),
    }


# =============================================================================
# PUBLIC API
# =============================================================================


# Compile the graph
document_analysis_graph = build_document_analysis_graph().compile()


async def analyze_document(
    document_id: str,
    tenant_id: str,
    text_content: str,
    filename: str,
    mime_type: str = "application/octet-stream",
    tier: str = "standard",
) -> DocumentAnalysisState:
    """Run the Document Analysis Agent on a document.

    This is the main entry point. Call this instead of the old
    enrich_document() pipeline.
    """
    initial_state: DocumentAnalysisState = {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "tier": tier,
        "text_content": text_content,
        "filename": filename,
        "mime_type": mime_type,
        "classification": None,
        "doc_type": "other",
        "classification_confidence": 0.0,
        "entities": [],
        "relationships": [],
        "resolved_entity_ids": [],
        "cross_doc_matches": [],
        "contradictions": [],
        "compliance_findings": [],
        "reasoning_chain": [],
        "retry_count": 0,
        "credits_consumed": 0.0,
        "status": "processing",
        "error": None,
    }

    logger.info(f"Document Analysis Agent starting: {filename} (tier={tier})")

    try:
        result = await document_analysis_graph.ainvoke(initial_state)
        logger.info(
            f"Document Analysis Agent completed: {filename} → {result.get('doc_type')} "
            f"({result.get('credits_consumed', 0):.1f} credits, "
            f"{len(result.get('entities', []))} entities, "
            f"{len(result.get('contradictions', []))} contradictions)"
        )
        return result
    except Exception as e:
        logger.exception(f"Document Analysis Agent failed: {filename}: {e}")
        initial_state["status"] = "error"
        initial_state["error"] = str(e)[:500]
        return initial_state
