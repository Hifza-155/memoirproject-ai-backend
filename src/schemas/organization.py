from typing import List, Optional
from pydantic import BaseModel, Field

class MemoryMapping(BaseModel):
    memory_id: str = Field(description="The exact UUID of the memory.")
    inferred_date: Optional[str] = Field(
        default=None,
        description="The inferred year, decade, or period based on the text. Null if indeterminate."
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