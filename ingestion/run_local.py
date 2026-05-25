import asyncio
import os
import sys
import hashlib
from dotenv import load_dotenv

load_dotenv()

from pipeline.extractor import extract_structure
from pipeline.parent_builder import build_parent_sections
from pipeline.chunker import chunk_section
from pipeline.embedder import embed_chunks, embed_texts
from pipeline.indexer import upsert_chunks, delete_document_chunks
from pipeline.blob_store import upload_parent_section, delete_document_blobs


async def ingest(file_path: str, source_url: str = ""):
    """Full ingestion pipeline: extract → build sections → chunk → embed → index."""
    document_title = os.path.basename(file_path).replace(".pdf", "").replace("-", " ")
    document_id = hashlib.md5(file_path.encode()).hexdigest()[:12]
    source_url = source_url or file_path

    print(f"\n[1/5] Extracting structure from {file_path}...")
    structure = extract_structure(file_path)
    print(f"      Found {len(structure['elements'])} elements.")

    print(f"[2/5] Building parent sections...")
    sections = build_parent_sections(structure, document_id, document_title, source_url)
    print(f"      {len(sections)} parent sections built.")

    print(f"[3/5] Generating child chunks...")
    all_chunks = []
    for section in sections:
        chunks = chunk_section(section, document_title)
        all_chunks.extend(chunks)
    print(f"      {len(all_chunks)} child chunks generated.")

    print(f"[4/5] Embedding child chunks...")
    all_chunks = await embed_chunks(all_chunks)

    print(f"[5/5] Uploading to Azure (Blob + AI Search)...")
    delete_document_blobs(document_id)
    delete_document_chunks(document_id)
    for section in sections:
        upload_parent_section(section)
    upsert_chunks(all_chunks)

    print(f"\nDone. Document '{document_title}' ingested successfully.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_local.py <path-to-pdf> [source-url]")
        sys.exit(1)
    url = sys.argv[2] if len(sys.argv) > 2 else ""
    asyncio.run(ingest(sys.argv[1], url))
