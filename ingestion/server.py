"""
Local HTTP server for the ingestion pipeline.
Run locally and expose via devtunnel for Power Automate integration.

Usage:
    python server.py
    # Then in another terminal:
    devtunnel host -p 7071 --allow-anonymous
"""

import asyncio
import base64
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

from pipeline.extractor import extract_structure_from_bytes
from pipeline.parent_builder import build_parent_sections
from pipeline.chunker import chunk_section
from pipeline.embedder import embed_chunks
from pipeline.indexer import upsert_chunks, delete_document_chunks
from pipeline.blob_store import upload_parent_section, delete_document_blobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="HR Ingestion Pipeline", version="1.0.0")


# ── Request models ────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    fileName: str
    fileId: str
    content: str  # base64-encoded file bytes
    fileUrl: Optional[str] = ""

class DeleteRequest(BaseModel):
    event: Optional[str] = "delete"
    fileId: str


# ── Endpoints ─────────────────────────────────────────────────────────

@app.post("/api/sharepoint_ingest")
async def sharepoint_ingest(req: IngestRequest):
    """
    Ingest a document from SharePoint via Power Automate.
    Receives base64-encoded file content, runs full pipeline.
    """
    logger.info(f"[Ingest] Processing file: {req.fileName} (fileId={req.fileId})")

    try:
        # Decode base64 content
        pdf_bytes = base64.b64decode(req.content)
        logger.info(f"[Ingest] Decoded {len(pdf_bytes)} bytes")

        document_id = req.fileId
        document_title = (
            os.path.splitext(req.fileName)[0]
            .replace("-", " ")
            .replace("_", " ")
        )
        source_url = req.fileUrl or req.fileName

        # Step 1: Extract structure
        logger.info("[Ingest] Step 1/5 — Extracting structure...")
        structure = extract_structure_from_bytes(pdf_bytes)
        logger.info(f"[Ingest]   Found {len(structure['elements'])} elements")

        # Step 2: Build parent sections
        logger.info("[Ingest] Step 2/5 — Building parent sections...")
        sections = build_parent_sections(
            structure, document_id, document_title, source_url
        )
        logger.info(f"[Ingest]   {len(sections)} parent sections built")

        # Step 3: Generate child chunks
        logger.info("[Ingest] Step 3/5 — Generating child chunks...")
        all_chunks = []
        for section in sections:
            chunks = chunk_section(section, document_title)
            all_chunks.extend(chunks)
        logger.info(f"[Ingest]   {len(all_chunks)} child chunks generated")

        # Step 4: Embed chunks
        logger.info("[Ingest] Step 4/5 — Embedding child chunks...")
        all_chunks = await embed_chunks(all_chunks)

        # Step 5: Upload to Azure (clean old data first)
        logger.info("[Ingest] Step 5/5 — Uploading to Azure...")
        delete_document_blobs(document_id)
        delete_document_chunks(document_id)
        for section in sections:
            upload_parent_section(section)
        upsert_chunks(all_chunks)

        msg = (
            f"Success: ingested {req.fileName} "
            f"({len(sections)} sections, {len(all_chunks)} chunks)"
        )
        logger.info(f"[Ingest] Done — {msg}")
        return {"status": "success", "message": msg}

    except Exception as e:
        logger.exception(f"[Ingest] Failed to process {req.fileName}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sharepoint_delete")
async def sharepoint_delete(req: DeleteRequest):
    """
    Delete all indexed data for a document removed from SharePoint.
    """
    logger.info(f"[Delete] Removing all data for fileId={req.fileId}")

    try:
        document_id = req.fileId
        delete_document_chunks(document_id)
        delete_document_blobs(document_id)

        msg = f"Deleted all data for fileId={req.fileId}"
        logger.info(f"[Delete] Done — {msg}")
        return {"status": "success", "message": msg}

    except Exception as e:
        logger.exception(f"[Delete] Failed to delete fileId={req.fileId}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ingestion-pipeline"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7071)
