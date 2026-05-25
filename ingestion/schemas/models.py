from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParentSection:
    document_id: str
    section_id: str
    heading: str
    full_text: str
    page_range: tuple[int, int]
    source_url: str


@dataclass
class ChildChunk:
    chunk_id: str
    document_id: str
    section_id: str
    section_heading: str
    document_title: str
    page_number: int
    source_url: str
    content: str
    content_vector: list[float] = field(default_factory=list)
    chunk_type: str = "text"   # "text" | "table"
