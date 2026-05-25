import tiktoken
import numpy as np
from schemas.models import ParentSection, ChildChunk
import hashlib

enc = tiktoken.get_encoding("cl100k_base")

TARGET_TOKENS = 350
OVERLAP_TOKENS = 50
SIMILARITY_THRESHOLD = 0.40


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def chunk_section(
    section: ParentSection,
    document_title: str,
    para_embeddings: dict[str, list[float]] | None = None
) -> list[ChildChunk]:
    """Split a parent section into child chunks with token-based and semantic boundaries."""
    chunks = []
    paragraphs = [p.strip() for p in section.full_text.split("\n\n") if p.strip()]

    current_tokens = []
    current_text_parts = []

    def flush_chunk(parts):
        text = "\n\n".join(parts)
        chunk_id = hashlib.md5(
            f"{section.section_id}:{text[:50]}".encode()
        ).hexdigest()[:16]
        return ChildChunk(
            chunk_id=chunk_id,
            document_id=section.document_id,
            section_id=section.section_id,
            section_heading=section.heading,
            document_title=document_title,
            page_number=section.page_range[0],
            source_url=section.source_url,
            content=text,
            chunk_type="text"
        )

    for i, para in enumerate(paragraphs):
        # Table special-casing: single chunk regardless of size
        if para.startswith("TABLE:") or (" | " in para and para.count("\n") > 1):
            if current_text_parts:
                chunks.append(flush_chunk(current_text_parts))
                current_text_parts = []
                current_tokens = []
            chunk_id = hashlib.md5(
                f"{section.section_id}:table:{i}".encode()
            ).hexdigest()[:16]
            chunks.append(ChildChunk(
                chunk_id=chunk_id,
                document_id=section.document_id,
                section_id=section.section_id,
                section_heading=section.heading,
                document_title=document_title,
                page_number=section.page_range[0],
                source_url=section.source_url,
                content=para,
                chunk_type="table"
            ))
            continue

        # Semantic boundary guard
        if para_embeddings and i > 0:
            prev_para = paragraphs[i - 1]
            if (prev_para in para_embeddings and para in para_embeddings):
                sim = cosine_similarity(
                    para_embeddings[prev_para],
                    para_embeddings[para]
                )
                if sim < SIMILARITY_THRESHOLD and current_text_parts:
                    chunks.append(flush_chunk(current_text_parts))
                    # Keep overlap
                    overlap_text = current_text_parts[-1] if current_text_parts else ""
                    overlap_toks = enc.encode(overlap_text)[-OVERLAP_TOKENS:]
                    current_text_parts = [enc.decode(overlap_toks)] if overlap_toks else []
                    current_tokens = list(overlap_toks)

        para_tokens = enc.encode(para)
        if len(current_tokens) + len(para_tokens) > TARGET_TOKENS and current_text_parts:
            chunks.append(flush_chunk(current_text_parts))
            overlap_toks = current_tokens[-OVERLAP_TOKENS:]
            current_text_parts = [enc.decode(overlap_toks)] if overlap_toks else []
            current_tokens = list(overlap_toks)

        current_text_parts.append(para)
        current_tokens.extend(para_tokens)

    if current_text_parts:
        chunks.append(flush_chunk(current_text_parts))

    return chunks
