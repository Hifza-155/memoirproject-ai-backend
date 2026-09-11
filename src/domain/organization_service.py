import os
import json
from openai import OpenAI
from src.schemas.organization import MemoirOrganizationOutput
from src.integrations.organization_repository import (
    fetch_memories_for_ai,
    apply_ai_organization
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
            "You must return a valid JSON object strictly matching this schema:\n"
            "{\n"
            '  "chapters": [\n'
            "    {\n"
            '      "title": "string",\n'
            '      "summary": "string or null",\n'
            '      "sort_order": 1,\n'
            '      "memories": [\n'
            '        {"memory_id": "string", "inferred_date": "string or null"}\n'
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