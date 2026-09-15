from typing import List, Optional , Literal
from pydantic import BaseModel, Field 
class MemoryMapping(BaseModel):
    memory_id: str = Field(description="The exact UUID of the memory.")
    inferred_date: Optional[Literal["day", "month", "year", "decade"]] = Field(
        default=None,
        description="The precision of the date. Must be strictly one of: 'day', 'month', 'year', or 'decade'."
    )
class ChapterOutput(BaseModel):
    title: str = Field(description="A distinct, chronological title for this chapter.")
    summary: Optional[str] = Field(
        default=None,
        description="A 1-2 sentence overview synthesizing the themes of the memories in this chapter."
    )
    sort_order: int = Field(description="The chronological sequence order (1, 2, 3...).")
    memories: List[MemoryMapping] = Field(description="List of memories assigned to this chapter.")

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
    
class ChatRequest(BaseModel):
    message: str = Field(description="The user's prompt or question for the AI co-author.")

class ChatResponse(BaseModel):
    success: bool = True
    reply: str = Field(description="Gemini's contextual response regarding the archive.")