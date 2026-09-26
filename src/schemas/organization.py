from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

class MemoryMapping(BaseModel):
    memory_id: str = Field(description="The exact UUID of the memory.")
    inferred_date: Optional[str] = Field(default="day")
    
    # NEW: The AI rewrites the specific memory here so it flows from the previous one
    woven_text: str = Field(
        description="The rewritten portion of the narrative specifically corresponding to this memory's media and events. It must flow seamlessly from the previous memory's text like a continuous book."
    )
    #Catch AI formatting errors before they crash the router
    @field_validator("inferred_date", mode="before")
    @classmethod
    def sanitize_precision(cls, value: Optional[str]) -> str:
        if not value or value not in ["day", "month", "year", "decade"]:
            return "day"
        return value

class ChapterOutput(BaseModel):
    title: str = Field(description="A distinct, chronological title for this chapter.")
    sort_order: int = Field(description="The chronological sequence order.")
    memories: List[MemoryMapping] = Field(description="List of memories assigned to this chapter, in chronological order.")
    
class MemoirOrganizationOutput(BaseModel):
    chapters: List[ChapterOutput] = Field(description="List of chronological chapters covering all provided memories.")

class OrganizeResponseEnvelope(BaseModel):
    success: bool = True
    message: str = "Organization started in the background."
    
class ChapterUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="The new title chosen by the user.")
    summary: Optional[str] = Field(None, description="The new summary chosen by the user.")

class MemoryMoveRequest(BaseModel):
    new_chapter_id: str = Field(description="The ID of the chapter this memory should be moved to.")
    
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(
        description="The role of the speaker, strictly 'user' or 'assistant'."
    )
    content: str = Field(
        max_length=2000, 
        description="The text content of the message, capped at 2000 characters."
    )

class ChatRequest(BaseModel):
    message: str = Field(
        max_length=2000, 
        description="The user's latest prompt or question for the AI co-author."
    )
    history: Optional[List[ChatMessage]] = Field(
        default=[], 
        max_length=20, 
        description="Past conversation turns for context, capped at 20 turns."
    )

class ChatResponse(BaseModel):
    success: bool = True
    reply: str = Field(description="Gemini's contextual response regarding the archive.")