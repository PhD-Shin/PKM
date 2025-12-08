"""
Note Service
Handles business logic for note management, including synchronization and AI processing.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import BackgroundTasks

from app.config import settings
from app.db.neo4j import get_neo4j_client
from app.services.graph_service import upsert_note, get_note, get_all_notes
from app.services.llm_client import summarize_content
from app.services.context_service import get_note_context
from app.services.graph_visualization_service import get_note_graph_vis
from app.utils.cache import TTLCache

logger = logging.getLogger(__name__)

# Feature flag for Graphiti
USE_GRAPHITI = getattr(settings, 'use_graphiti', False)

# Rate limiting: AI processing limit
_ai_semaphore = asyncio.Semaphore(2)
_AI_PROCESSING_DELAY = 1.0


class NoteService:
    def __init__(self):
        self.context_cache = TTLCache(ttl_seconds=300)
        self.graph_cache = TTLCache(ttl_seconds=300)

    async def sync_note(
        self,
        user_id: str,
        vault_id: str,
        note_data: Dict[str, Any],
        privacy_mode: str,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """
        Syncs a note to Neo4j and schedules background AI processing.
        """
        client = get_neo4j_client()
        
        # 1. Save to Neo4j
        success = upsert_note(
            client=client,
            user_id=user_id,
            vault_id=vault_id,
            note_data=note_data,
        )

        if not success:
            raise Exception("Failed to save note to database")

        # 2. Prepare content for AI processing
        content_for_ai = note_data.get("content", "")
        if privacy_mode == "summary":
            content_for_ai = summarize_content(content_for_ai)
        elif privacy_mode == "metadata":
            content_for_ai = ""

        ai_scheduled = False
        if content_for_ai:
            background_tasks.add_task(
                self.process_note_background,
                note_id=note_data["note_id"],
                content=content_for_ai,
                tags=note_data.get("tags", []),
                path=note_data.get("path", ""),
                title=note_data.get("title", ""),
                created_at=note_data.get("created_at", ""),
                updated_at=note_data.get("updated_at", "")
            )
            ai_scheduled = True
            logger.info(f"📋 AI processing scheduled for: {note_data['note_id'][:50]}...")

        message = "Note synced successfully"
        if ai_scheduled:
            message += ". AI processing scheduled in background."

        return {
            "status": "success",
            "note_id": note_data["note_id"],
            "message": message,
        }

    async def process_note_background(
        self,
        note_id: str,
        content: str,
        tags: List[str],
        path: str,
        title: str,
        created_at: str,
        updated_at: str
    ):
        """
        Background AI processing: Entity extraction and Embedding generation.
        """
        async with _ai_semaphore:
            await asyncio.sleep(_AI_PROCESSING_DELAY)

            try:
                logger.info(f"🔄 Background AI processing started for: {note_id[:50]}...")

                # 1. Entity Extraction
                if USE_GRAPHITI:
                    from app.services.hybrid_graphiti_service import process_note_hybrid
                    
                    note_updated_at = datetime.now()
                    if updated_at:
                        try:
                            updated_str = updated_at.replace('Z', '+00:00')
                            note_updated_at = datetime.fromisoformat(updated_str)
                        except (ValueError, AttributeError):
                            pass

                    hybrid_result = await process_note_hybrid(
                        note_id=note_id,
                        content=content,
                        updated_at=note_updated_at,
                        metadata={
                            "tags": tags,
                            "path": path,
                            "title": title,
                            "created_at": created_at
                        }
                    )
                    extracted_nodes = hybrid_result.get("nodes_extracted", 0)
                    pkm_labels = hybrid_result.get("pkm_labels_added", 0)
                    mentions = hybrid_result.get("mentions_created", 0)
                    logger.info(f"✅ Hybrid mode: {extracted_nodes} entities, {pkm_labels} PKM labels, {mentions} MENTIONS")
                else:
                    from app.services.ontology_service import process_note_to_graph
                    extracted_nodes = process_note_to_graph(
                        note_id=note_id,
                        content=content,
                        metadata={"tags": tags}
                    )
                    logger.info(f"✅ Extracted {extracted_nodes} entities from note")

                # 2. Embedding Generation
                from app.services.vector_service import store_note_embedding
                embedding_created = store_note_embedding(
                    note_id=note_id,
                    content=content,
                    metadata={"tags": tags}
                )

                if embedding_created:
                    logger.info(f"✅ Embedding created for note: {note_id[:50]}")

                # Invalidate caches
                self.context_cache.clear(note_id)
                self.graph_cache.clear_prefix(f"{note_id}:")

            except Exception as e:
                logger.error(f"❌ Background AI processing failed for {note_id[:50]}: {e}", exc_info=True)

    def delete_note(self, note_id: str, user_id: str) -> Dict[str, Any]:
        """
        Deletes a note and cleans up orphan entities.
        """
        try:
            client = get_neo4j_client()
            logger.info(f"🗑️ Deleting note: {note_id}")

            # Step 1: Delete Note and relations
            cypher_delete_note = """
            MATCH (n:Note {note_id: $note_id})
            OPTIONAL MATCH (n)-[m:MENTIONS]->(e:Entity)
            OPTIONAL MATCH (v:Vault)-[h:HAS_NOTE]->(n)
            DELETE m, h, n
            RETURN count(n) as deleted_notes
            """

            result = client.query(cypher_delete_note, {"note_id": note_id})
            deleted_notes = result[0]["deleted_notes"] if result else 0

            # Step 2: Cleanup orphans
            cypher_cleanup_orphan_entities = """
            MATCH (e:Entity)
            WHERE NOT (e)<-[:MENTIONS]-(:Note)
              AND NOT (e)<-[:MENTIONS]-(:Episodic)
            WITH e
            OPTIONAL MATCH (e)-[r:RELATES_TO]-()
            DELETE r, e
            RETURN count(e) as orphans_deleted
            """

            cleanup_result = client.query(cypher_cleanup_orphan_entities, {})
            orphans_deleted = cleanup_result[0]["orphans_deleted"] if cleanup_result else 0

            # Invalidate caches
            self.context_cache.clear(note_id)
            self.graph_cache.clear_prefix(f"{note_id}:")

            logger.info(f"✅ Note deleted: {note_id}, orphan entities cleaned: {orphans_deleted}")

            return {
                "status": "success",
                "message": "Note deleted successfully",
                "note_id": note_id,
                "deleted_notes": deleted_notes,
                "orphans_cleaned": orphans_deleted
            }
        except Exception as e:
            logger.error(f"Failed to delete note {note_id}: {e}")
            raise Exception(f"Failed to delete note: {str(e)}")

    def get_context(self, note_id: str) -> Dict[str, Any]:
        """
        Get note context with caching.
        """
        cached = self.context_cache.get(note_id)
        if cached:
            return cached

        context = get_note_context(note_id=note_id, content_preview=note_id)
        self.context_cache.set(note_id, context)
        return context

    def get_graph(self, note_id: str, hops: int = 1) -> Dict[str, Any]:
        """
        Get note graph with caching.
        """
        cache_key = f"{note_id}:{hops}"
        cached = self.graph_cache.get(cache_key)
        if cached:
            return cached

        graph = get_note_graph_vis(note_id=note_id, hops=hops)
        self.graph_cache.set(cache_key, graph)
        return graph

# Global instance
note_service = NoteService()
