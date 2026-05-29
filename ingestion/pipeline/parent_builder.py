import hashlib
import logging
import tiktoken
from schemas.models import ParentSection

enc = tiktoken.get_encoding("cl100k_base")


def build_parent_sections(
    structure: dict,
    document_id: str,
    document_title: str,
    source_url: str
) -> list[ParentSection]:
    """Build parent sections from extracted document structure by splitting on headings."""
    elements = structure["elements"]
    sections = []
    current_heading = document_title
    current_elements = []
    current_start_page = 1

    def flush(heading, elems, start_page, end_page):
        if not elems:
            return None
        full_text = "\n\n".join(e["content"] for e in elems)
        token_count = len(enc.encode(full_text))
        # Warn if outside target range
        if not (1500 <= token_count <= 2500):
            logging.warning(f"Section '{heading}' has {token_count} tokens (target: 1500–2500)")
        section_id = hashlib.md5(
            f"{document_id}:{heading}".encode()
        ).hexdigest()[:12]
        return ParentSection(
            document_id=document_id,
            section_id=section_id,
            heading=heading,
            full_text=full_text,
            page_range=(start_page, end_page),
            source_url=source_url
        )

    for elem in elements:
        if elem["type"] == "heading" and elem["level"] in (1, 2):
            section = flush(
                current_heading, current_elements,
                current_start_page,
                current_elements[-1]["page"] if current_elements else 1
            )
            if section:
                sections.append(section)
            current_heading = elem["content"]
            current_elements = []
            current_start_page = elem["page"]
        else:
            current_elements.append(elem)

    # flush last section
    last_page = current_elements[-1]["page"] if current_elements else 1
    section = flush(current_heading, current_elements, current_start_page, last_page)
    if section:
        sections.append(section)

    return sections
