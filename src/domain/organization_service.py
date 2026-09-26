import os
import json
import asyncio
import logging
from datetime import datetime
from src.core.config import settings  
from openai import OpenAI
from src.schemas.organization import MemoirOrganizationOutput, ChapterOutput, MemoryMapping
from src.integrations.organization_repository import (
    fetch_memories_for_ai,
    apply_ai_organization,
    fetch_archive_raw_data,
    update_generation_status 
)

logger = logging.getLogger(__name__)

def get_ai_client() -> OpenAI:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("CRITICAL: GEMINI_API_KEY is missing in environment variables.")
    
    # Using the OpenAI SDK wrapper for Gemini
    # max_retries=0 is CRITICAL: it prevents the SDK from aggressively panic-spamming
    # the server when we hit a 503, allowing our smart call_ai_with_retry backoff to work.
    return OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        max_retries=0 
    )

def sort_memories_chronologically(memories: list) -> list:
    """Python-level chronological sorting to guarantee timeline accuracy."""
    def parse_date(date_str):
        if not date_str:
            return datetime.max
        try:
            date_part = str(date_str).split('T')[0]
            return datetime.strptime(date_part, "%Y-%m-%d")
        except Exception:
            return datetime.max
    return sorted(memories, key=lambda m: parse_date(m.get("occurred_start")))

async def call_ai_with_retry(client, messages, max_retries=4):
    """Robust exponential backoff helper for all AI calls."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.gemini_model,
                messages=messages,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e).lower()
            # 503 Overloaded or 429 Too Many Requests
            if "503" in error_str or "overloaded" in error_str or "429" in error_str:
                if attempt == max_retries - 1:
                    raise e
                
                delay = 3 * (2 ** attempt) # 3s, 6s, 12s backoff
                logger.warning(f"AI API limit hit. Retrying in {delay} seconds...")
                await asyncio.sleep(delay) 
            else:
                # If it's a completely different error, fail immediately
                raise e

async def perform_background_organization(memoir_id: str):
    """
    PRODUCTION-GRADE MULTI-PASS PIPELINE:
    Pass 1: Architect clusters the structure.
    Pass 2: Ghostwriter loops through chapters to rewrite prose perfectly.
    """
    update_generation_status(memoir_id, "processing")
    
    memories = fetch_memories_for_ai(memoir_id)
    if not memories:
        logger.warning(f"No memories found for {memoir_id}.")
        update_generation_status(memoir_id, "failed", "No memories found.")
        return

    sorted_memories = sort_memories_chronologically(memories)
    
    try:
        client = get_ai_client()
    except Exception as e:
        update_generation_status(memoir_id, "failed", str(e))
        return

    try:
        # ==========================================
        # PASS 1: THE ARCHITECT (Clustering Only)
        # ==========================================
        logger.info(f"Starting Pass 1 (Structure) for {memoir_id}")
        
        architect_payload = [{"memory_id": str(m["id"]), "text": m.get("body_text")} for m in sorted_memories]
        
        architect_prompt = (
            "You are an archival structural architect. Group these chronological memories into thematic chapters. "
            "Do NOT rewrite text. Just return the JSON structure.\n"
            "CRITICAL RULES:\n"
            "1. You MUST assign EVERY SINGLE memory_id from the input to a chapter.\n"
            "2. Do not omit, drop, or skip any memories. If I give you 10 memories, your JSON must contain exactly 10 memory_ids across the chapters.\n\n"
            "Return JSON matching this schema:\n"
            '{"chapters": [{"title": "Chapter Name", "sort_order": 1, "memory_ids": ["uuid-1", "uuid-2"]}]}'
        )
        
        architect_content = await call_ai_with_retry(client, [
            {"role": "system", "content": architect_prompt},
            {"role": "user", "content": json.dumps(architect_payload)}
        ])
        
        structure_data = json.loads(architect_content)
        chapters_structure = structure_data.get("chapters", [])

        # ==========================================
        # PASS 2: THE GHOSTWRITER (Chapter-by-Chapter Rewriting)
        # ==========================================
        logger.info(f"Starting Pass 2 (Narrative) for {memoir_id} - Processing {len(chapters_structure)} chapters.")
        
        final_chapters = []
        
        for index, chapter in enumerate(chapters_structure):
            chapter_title = chapter.get("title", "Untitled Chapter")
            chapter_sort = chapter.get("sort_order", 1)
            memory_ids_in_chapter = chapter.get("memory_ids", [])
            
            # Get the real memory objects for this specific chapter
            raw_chapter_memories = [m for m in sorted_memories if str(m["id"]) in memory_ids_in_chapter]
            
            if not raw_chapter_memories:
                continue

            writer_payload = [{"memory_id": str(m["id"]), "text": m.get("body_text")} for m in raw_chapter_memories]
            
            writer_prompt = (
                f"You are a Pulitzer-prize winning biographer writing a book chapter titled '{chapter_title}'.\n"
                "I am providing the raw voice notes for this chapter. You MUST rewrite and polish the 'text' of EVERY memory into beautiful, flowing paragraphs.\n"
                "CRITICAL RULES:\n"
                "1. You are STRICTLY FORBIDDEN from copying the original input text. You must fix all transcription errors.\n"
                "2. You MUST return a rewritten output for EVERY SINGLE memory_id provided in the input. Do not combine or skip any memories.\n\n"
                "Return JSON matching this schema exactly:\n"
                '{"rewritten_memories": [{"memory_id": "uuid-here", "inferred_date": "day", "woven_text": "Your beautiful rewritten paragraph goes here."}]}'
            )

            logger.info(f"  -> Pass 2: Rewriting Chapter {index + 1}: '{chapter_title}'")
            
            writer_content = await call_ai_with_retry(client, [
                {"role": "system", "content": writer_prompt},
                {"role": "user", "content": json.dumps(writer_payload)}
            ])
            
            writer_data = json.loads(writer_content)
            rewritten_memories = writer_data.get("rewritten_memories", [])
            
            # Map the AI outputs into our Pydantic schema
            memory_mappings = []
            for rm in rewritten_memories:
                memory_mappings.append(MemoryMapping(
                    memory_id=rm.get("memory_id"),
                    inferred_date=rm.get("inferred_date", "day"),
                    woven_text=rm.get("woven_text", "")
                ))
                
            final_chapters.append(ChapterOutput(
                title=chapter_title,
                sort_order=chapter_sort,
                memories=memory_mappings
            ))
            
            # Wait 4 seconds between chapter generations to guarantee we avoid rate limits
            await asyncio.sleep(4)

        # ==========================================
        # FINAL ASSEMBLY & PERSISTENCE
        # ==========================================
        validated_output = MemoirOrganizationOutput(chapters=final_chapters)
        apply_ai_organization(memoir_id, validated_output.model_dump())
        
        logger.info(f"Multi-Pass AI organization successfully completed for {memoir_id}.")
        update_generation_status(memoir_id, "completed")
        
    except Exception as e:
        error_msg = f"AI organization job failed: {str(e)}"
        logger.error(f"{error_msg} for memoir {memoir_id}")
        update_generation_status(memoir_id, "failed", error_msg)

# ==========================================
# CHAT CONTEXT HELPER
# ==========================================
def get_archive_context_for_chat(memoir_id: str) -> str:
    """
    Builds a summary of the current memoir structure so the AI assistant
    knows what chapters/memories already exist.
    """
    try:
        raw_data = fetch_archive_raw_data(memoir_id)
        chapters = raw_data.get("chapters", [])
        
        if not chapters:
            return "The archive is currently empty and unorganized."
            
        context_parts = ["Current Memoir Structure:"]
        for ch in chapters:
            context_parts.append(f"\nChapter: {ch['title']}")
            memories = ch.get("memories", [])
            for m in memories:
                # Include woven_text if it exists, otherwise fall back to body_text
                text = m.get("ai_woven_text") or m.get("body_text", "No text provided")
                snippet = text[:150] + "..." if len(text) > 150 else text
                context_parts.append(f"  - Memory: {snippet}")
                
        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Failed to build chat context for {memoir_id}: {e}")
        return "Could not retrieve archive structure."