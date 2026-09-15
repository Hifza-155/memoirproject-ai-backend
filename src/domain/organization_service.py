import os
import json
from openai import OpenAI
from src.schemas.organization import MemoirOrganizationOutput
from src.integrations.organization_repository import (
    fetch_memories_for_ai,
    apply_ai_organization,
    fetch_archive_raw_data
)

# Note the exact base_url with "v1beta" and the trailing "/"
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def perform_background_organization(memoir_id: str):
    """
    Background worker orchestrating memory fetching, structured LLM clustering,
    and database persistence using Gemini via the OpenAI interface.
    """
    try:
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
            "You are an archival biographer organizing raw memories of a person's life into chapters. "
            "Group the memories chronologically into thematic life chapters. "
            "Ensure each chapter title is unique within the memoir. "
            "Provide a concise summary for each chapter. "
            "Assign every memory to a chapter without rewriting, altering, or omitting any content. "
            "CRITICAL REQUIREMENT FOR 'inferred_date': For each memory mapping, the 'inferred_date' field must strictly be one of these four exact lowercase words: 'day', 'month', 'year', or 'decade' representing the precision of the date. Do not put calendar dates like '2026-09-01'. "
            "You must return a valid JSON object strictly matching this schema:\n"
            "{\n"
            '  "chapters": [\n'
            "    {\n"
            '      "title": "string",\n'
            '      "summary": "string or null",\n'
            '      "sort_order": 1,\n'
            '      "memories": [\n'
            '        {"memory_id": "string", "inferred_date": "day"}\n'
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        
        response = client.chat.completions.create(
            model="gemini-3.6-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload_for_llm)}
            ],
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        
        # Validate against your Pydantic schema
        validated_output = MemoirOrganizationOutput.model_validate_json(content)
        
        apply_ai_organization(memoir_id, validated_output.model_dump())
        print(f"AI organization successfully applied for memoir {memoir_id}.")

    except Exception as e:
        print(f"AI organization job failed for memoir {memoir_id}: {str(e)}")
        
def get_archive_context_for_chat(memoir_id: str) -> str:
    """Calls the repository to fetch data and formats it into text for Gemini's context."""
    raw_data = fetch_archive_raw_data(memoir_id)
    chapters = raw_data.get("chapters", [])
    memories = raw_data.get("memories", [])

    # Build a clean text representation of the archive
    context_str = "CURRENT ARCHIVE STRUCTURE:\n\n"
    
    for ch in chapters:
        context_str += f"Chapter {ch.get('sort_order')}: {ch.get('title')}\n"
        context_str += f"Summary: {ch.get('summary') or 'None'}\n"
        context_str += "Memories in this chapter:\n"
        
        ch_memories = [m for m in memories if m.get("chapter_id") == ch.get("id")]
        if not ch_memories:
            context_str += "  - (No memories assigned yet)\n"
        for m in ch_memories:
            body = m.get('body_text')
            snippet = body[:100] if body else 'Audio/Photo memory'
            context_str += f"  - Title: '{m.get('title') or 'Untitled'}', Text: {snippet}\n"
        context_str += "\n"
        
    # Include unassigned memories if any
    unassigned = [m for m in memories if not m.get("chapter_id")]
    if unassigned:
        context_str += "Unassigned Memories:\n"
        for m in unassigned:
            context_str += f"  - Title: '{m.get('title') or 'Untitled'}'\n"
            
    return context_str