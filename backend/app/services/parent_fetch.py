import os
import json
from azure.storage.blob import BlobServiceClient

_blob_client = None
MAX_CITATIONS = 3


def get_blob_client():
    global _blob_client
    if not _blob_client:
        _blob_client = BlobServiceClient.from_connection_string(
            os.environ["AZURE_BLOB_CONNECTION_STRING"]
        )
    return _blob_client


def fetch_parent_section(document_id: str, section_id: str) -> dict | None:
    """Fetch a parent section JSON from Azure Blob Storage."""
    try:
        container = os.environ["AZURE_BLOB_CONTAINER"]
        blob_path = f"documents/{document_id}/sections/{section_id}.json"
        client = get_blob_client()
        blob = client.get_blob_client(container=container, blob=blob_path)
        data = blob.download_blob().readall()
        return json.loads(data)
    except Exception:
        return None


def assemble_context(chunks: list[dict], token_budget: int = 6000) -> tuple[list[dict], list[dict]]:
    """
    Fetch parent sections for each unique section_id.
    Returns (parent_sections, citations).
    Truncates at token_budget to leave room for GPT-4o output.
    """
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")

    seen = {}
    citations = []
    parent_sections = []
    total_tokens = 0

    for chunk in chunks:
        sid = chunk["section_id"]
        did = chunk["document_id"]
        if sid in seen:
            continue
        seen[sid] = True

        section = fetch_parent_section(did, sid)
        if not section:
            # Fallback: use the child chunk content itself
            section = {
                "heading": chunk.get("section_heading", "Unknown"),
                "full_text": chunk.get("content", ""),
                "source_url": chunk.get("source_url", "")
            }

        section_tokens = len(enc.encode(section.get("full_text", "")))
        if total_tokens + section_tokens > token_budget:
            # Truncate at paragraph boundary
            paragraphs = section["full_text"].split("\n\n")
            truncated = []
            tok_count = 0
            for para in paragraphs:
                para_toks = len(enc.encode(para))
                if tok_count + para_toks > (token_budget - total_tokens):
                    break
                truncated.append(para)
                tok_count += para_toks
            section["full_text"] = "\n\n".join(truncated)
            section["truncated"] = True

        total_tokens += len(enc.encode(section.get("full_text", "")))
        parent_sections.append(section)
        citations.append({
            "heading": section.get("heading", chunk.get("section_heading", "")),
            "url": section.get("source_url", chunk.get("source_url", ""))
        })

        if total_tokens >= token_budget:
            break

    return parent_sections, citations


def limit_citations(citations: list[dict], max_items: int = MAX_CITATIONS) -> list[dict]:
    """Keep a short, deduplicated citation list for the UI."""
    trimmed: list[dict] = []
    seen: set[str] = set()

    for citation in citations:
        heading = citation.get("heading", "").strip()
        if not heading:
            continue
        normalized = heading.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        trimmed.append({"heading": heading, "url": citation.get("url", "")})
        if len(trimmed) >= max_items:
            break

    return trimmed
