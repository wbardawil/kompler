"""Entity resolution — the engine that makes the knowledge graph grow.

When a new document is enriched, every extracted entity is resolved against
the existing knowledge graph. This creates the "Obsidian backlinks" effect:
- "Acme Corp" in Doc A matches "ACME Corporation" in Doc B → automatic link
- "ISO 9001:2015" in 15 documents → one node connecting all 15

Three-tier matching:
  1. Exact match on canonical_name (fast, free)
  2. Embedding cosine similarity via pgvector (accurate, fast)
     - > 0.85: auto-merge
     - 0.70-0.85: ambiguous (log for review)
     - < 0.70: create new entity
  3. Claude disambiguation for ambiguous cases (optional, costs credits)
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.models import Entity, ResolvedEntity

logger = logging.getLogger(__name__)
settings = get_settings()


class EntityResolver:
    """Resolve extracted entities against the existing knowledge graph."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.stats = {
            "exact_matches": 0,
            "embedding_matches": 0,
            "ambiguous": 0,
            "new_entities": 0,
        }

    async def resolve(
        self,
        entity_value: str,
        entity_type: str,
        embedding: list[float] | None = None,
    ) -> tuple[ResolvedEntity, str]:
        """Resolve an entity against existing graph nodes.

        Returns (resolved_entity, resolution_type) where resolution_type is one of:
        'exact_match', 'embedding_match', 'ambiguous', 'new'
        """
        # Tier 1: Exact match on canonical_name (case-insensitive)
        result = await self.session.execute(
            select(ResolvedEntity).where(
                ResolvedEntity.tenant_id == self.tenant_id,
                ResolvedEntity.entity_type == entity_type,
                func.lower(ResolvedEntity.canonical_name) == entity_value.lower(),
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            self.stats["exact_matches"] += 1
            logger.debug(f"Exact match: '{entity_value}' → '{existing.canonical_name}'")
            return existing, "exact_match"

        # Tier 2: Embedding similarity via pgvector
        if embedding:
            match = await self._embedding_match(entity_value, entity_type, embedding)
            if match:
                resolved, similarity = match
                if similarity >= settings.entity_resolution_threshold:  # 0.85
                    self.stats["embedding_matches"] += 1
                    # Add as alias
                    await self._add_alias(resolved, entity_value)
                    logger.info(
                        f"Embedding match ({similarity:.2f}): '{entity_value}' → '{resolved.canonical_name}'"
                    )
                    return resolved, "embedding_match"
                elif similarity >= settings.entity_resolution_ambiguous:  # 0.70
                    self.stats["ambiguous"] += 1
                    # Create new but log as ambiguous for review
                    new_entity = await self._create_new(entity_value, entity_type, embedding)
                    await self._log_resolution(
                        new_entity.id,
                        resolved.id,
                        "ambiguous",
                        similarity,
                        f"Possible match with '{resolved.canonical_name}' ({similarity:.2f})",
                    )
                    logger.info(
                        f"Ambiguous ({similarity:.2f}): '{entity_value}' ↔ '{resolved.canonical_name}'"
                    )
                    return new_entity, "ambiguous"

        # Tier 3: Create new resolved entity
        self.stats["new_entities"] += 1
        new_entity = await self._create_new(entity_value, entity_type, embedding)
        logger.debug(f"New entity: '{entity_value}' ({entity_type})")
        return new_entity, "new"

    async def _embedding_match(
        self,
        entity_value: str,
        entity_type: str,
        embedding: list[float],
    ) -> tuple[ResolvedEntity, float] | None:
        """Find the closest matching resolved entity by embedding similarity."""
        # Use $N params for asyncpg compatibility with pgvector
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        result = await self.session.execute(
            text(
                "SELECT id, canonical_name, entity_type, "
                "1 - (embedding <=> cast(:embedding as vector)) as similarity "
                "FROM resolved_entities "
                "WHERE tenant_id = :tenant_id "
                "AND entity_type = :entity_type "
                "AND embedding IS NOT NULL "
                "ORDER BY embedding <=> cast(:embedding2 as vector) "
                "LIMIT 1"
            ),
            {
                "tenant_id": str(self.tenant_id),
                "entity_type": entity_type,
                "embedding": embedding_str,
                "embedding2": embedding_str,
            },
        )
        row = result.mappings().first()

        if row and row["similarity"] >= settings.entity_resolution_ambiguous:
            resolved = await self.session.get(ResolvedEntity, row["id"])
            if resolved:
                return resolved, row["similarity"]

        return None

    async def _create_new(
        self,
        entity_value: str,
        entity_type: str,
        embedding: list[float] | None = None,
    ) -> ResolvedEntity:
        """Create a new resolved entity node in the graph."""
        resolved = ResolvedEntity(
            tenant_id=self.tenant_id,
            entity_type=entity_type,
            canonical_name=entity_value,
        )
        self.session.add(resolved)
        await self.session.flush()

        # Set embedding via raw SQL (pgvector type)
        if embedding:
            await self.session.execute(
                text("UPDATE resolved_entities SET embedding = :emb WHERE id = :id"),
                {"emb": str(embedding), "id": str(resolved.id)},
            )

        return resolved

    async def _add_alias(self, resolved: ResolvedEntity, alias: str) -> None:
        """Add an alias name to a resolved entity."""
        # For now, store in properties JSONB
        props = resolved.properties or {}
        aliases = props.get("aliases", [])
        if alias.lower() not in [a.lower() for a in aliases]:
            aliases.append(alias)
            props["aliases"] = aliases
            resolved.properties = props

    async def _log_resolution(
        self,
        entity_id: uuid.UUID,
        candidate_id: uuid.UUID,
        resolution_type: str,
        similarity: float,
        reasoning: str,
    ) -> None:
        """Log entity resolution decision for audit trail."""
        await self.session.execute(
            text("""
                INSERT INTO entity_resolution_log
                    (tenant_id, entity_id, resolved_entity_id, resolution_type,
                     similarity_score, reasoning)
                VALUES (:tenant_id, :entity_id, :candidate_id, :resolution_type,
                        :similarity, :reasoning)
            """),
            {
                "tenant_id": str(self.tenant_id),
                "entity_id": str(entity_id),
                "candidate_id": str(candidate_id),
                "resolution_type": resolution_type,
                "similarity": similarity,
                "reasoning": reasoning,
            },
        )
