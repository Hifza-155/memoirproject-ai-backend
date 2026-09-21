import os
import json
import asyncio
from openai import OpenAI
from src.schemas.organization import MemoirOrganizationOutput
from src.integrations.organization_repository import (
    fetch_memories_for_ai,
    apply_ai_organization,
    fetch_archive_raw_data
)

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

async def perform_background_organization(memoir_id: str):
    """
    Background worker orchestrating memory fetching, structured LLM clustering,
    and database persistence with exponential backoff for 503 limits.
    """
    memories = fetch_memories_for_ai(memoir_id)
    if not memories:
        print(f"No submitted memories found for memoir {memoir_id}.")
        return

    payload_for_llm = [
        {
            "memory_id": str(m["id"]),
            "title": m.get("title") or "",
            "text": m.get("body_text") or "",
            "recorded_date": m.get("occurred_start") or ""
        }
        for m in memories
    ]

    system_prompt = (
        "You are an archival biographer organizing raw memories into published book chapters. "
        "Review all provided memories, cluster them chronologically into thematic chapters, and assign every single memory to a chapter. "
        "For each chapter, you must provide:\n"
        "1. 'title': A distinct, chronological title for the chapter.\n"
        "2. 'sort_order': An integer representing the chronological sequence order (starting from 1).\n"
        "3. 'memories': A list of memories assigned to this chapter.\n\n"
        "For each memory object, include:\n"
        "- 'memory_id': The exact UUID provided in the input.\n"
        "- 'inferred_date': 'day', 'month', 'year', or 'decade'.\n"
        "- 'woven_text': The rewritten, flowing narrative paragraph corresponding to this memory that connects smoothly with the surrounding story like a book.\n\n"
        "CRITICAL: Do not introduce any outside information or facts not present in the input memories. "
        "Return a valid JSON object strictly matching this exact schema:\n"
        "{\n"
        '  "chapters": [\n'
        "    {\n"
        '      "title": "string",\n'
        '      "sort_order": 1,\n'
        '      "memories": [\n'
        '        {"memory_id": "string", "inferred_date": "day", "woven_text": "string"}\n'
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}"
    )
    
    # FIX: Exponential backoff loop to silently retry on 503s
    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gemini-3.6-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload_for_llm)}
                ],
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            validated_output = MemoirOrganizationOutput.model_validate_json(content)
            apply_ai_organization(memoir_id, validated_output.model_dump())
            print(f"AI organization successfully applied for memoir {memoir_id}.")
            break  # Exit loop on success
            
        except Exception as e:
            error_str = str(e).lower()
            if "503" in error_str or "overloaded" in error_str or "429" in error_str:
                if attempt == max_retries - 1:
                    print(f"AI organization failed after {max_retries} attempts for {memoir_id}.")
                    return
                await asyncio.sleep(2 * (2 ** attempt)) # Waits 2s, 4s, 8s
            else:
                print(f"AI organization job failed for memoir {memoir_id}: {str(e)}")
                return

def get_archive_context_for_chat(memoir_id: str) -> str:
    """
    Optimized structural index for the AI co-author, now including raw text 
    so the AI isn't amnesiac during chats.
    """
    raw_data = fetch_archive_raw_data(memoir_id)
    chapters = raw_data.get("chapters", [])
    memories = raw_data.get("memories", [])

    context_str = "== MEMOIR ARCHIVE TABLE OF CONTENTS ==\n\n"
    
    for ch in chapters:
        context_str += f"Chapter {ch.get('sort_order')}: {ch.get('title')}\n"
        if ch.get('summary'):
            context_str += f"Summary/Narrative: {ch.get('summary')}\n"
        
        ch_memories = [m for m in memories if m.get("chapter_id") == ch.get("id")]
        if ch_memories:
            context_str += "Contained Memories:\n"
            for m in ch_memories:
                m_title = m.get('title') or 'Untitled'
                m_date = m.get('occurred_start') or 'Undated'
                # FIX: Include actual body text so the AI can answer detailed questions
                m_body = m.get('body_text') or ''
                context_str += f"  - [{m_date}] {m_title}: {m_body}\n"
        else:
            context_str += "  - (No memories assigned yet)\n"
        context_str += "\n"
        
    unassigned = [m for m in memories if not m.get("chapter_id")]
    if unassigned:
        context_str += "Unassigned Memories:\n"
        for m in unassigned:
            m_body = m.get('body_text') or ''
            context_str += f"  - Title: '{m.get('title') or 'Untitled'}': {m_body}\n"
            
    return context_str