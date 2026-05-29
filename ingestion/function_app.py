import azure.functions as func
import asyncio
import base64
import logging
import os

from pipeline.extractor import extract_structure_from_bytes
from pipeline.parent_builder import build_parent_sections
from pipeline.chunker import chunk_section
from pipeline.embedder import embed_chunks
from pipeline.indexer import upsert_chunks, delete_document_chunks
from pipeline.blob_store import upload_parent_section, delete_document_blobs

app = func.FunctionApp()


@app.route(route="sharepoint_ingest", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def sharepoint_ingest(req: func.HttpRequest) -> func.HttpResponse:
    """
    Ingest a document from SharePoint via Power Automate.

    Expected JSON body:
    {
        "fileName": "LeavePolicy.pdf",
        "fileUrl": "https://sharepoint.com/...",
        "fileId": "123",
        "content": "<base64-encoded file bytes>"
    }
    """
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    file_name = body.get("fileName")
    file_url = body.get("fileUrl", "")
    file_id = body.get("fileId")
    content_b64 = body.get("content")

    # ── Validate required fields ──────────────────────────────────────
    if not file_name or not file_id or not content_b64:
        return func.HttpResponse(
            "Missing required fields: fileName, fileId, content",
            status_code=400,
        )

    logging.info(f"[Ingest] Processing file: {file_name} (fileId={file_id})")

    try:
        # ── Decode base64 content ─────────────────────────────────────
        pdf_bytes = base64.b64decode(content_b64)
        logging.info(f"[Ingest] Decoded {len(pdf_bytes)} bytes")

        # Use fileId as document_id for consistent indexing / deletion
        document_id = file_id
        document_title = (
            os.path.splitext(file_name)[0]
            .replace("-", " ")
            .replace("_", " ")
        )
        source_url = file_url or file_name

        # ── Step 1: Extract structure ─────────────────────────────────
        logging.info("[Ingest] Step 1/5 — Extracting structure...")
        structure = extract_structure_from_bytes(pdf_bytes)
        logging.info(f"[Ingest]   Found {len(structure['elements'])} elements")

        # ── Step 2: Build parent sections ─────────────────────────────
        logging.info("[Ingest] Step 2/5 — Building parent sections...")
        sections = build_parent_sections(
            structure, document_id, document_title, source_url
        )
        logging.info(f"[Ingest]   {len(sections)} parent sections built")

        # ── Step 3: Generate child chunks ─────────────────────────────
        logging.info("[Ingest] Step 3/5 — Generating child chunks...")
        all_chunks = []
        for section in sections:
            chunks = chunk_section(section, document_title)
            all_chunks.extend(chunks)
        logging.info(f"[Ingest]   {len(all_chunks)} child chunks generated")

        # ── Step 4: Embed chunks ──────────────────────────────────────
        logging.info("[Ingest] Step 4/5 — Embedding child chunks...")
        all_chunks = asyncio.run(embed_chunks(all_chunks))

        # ── Step 5: Upload to Azure (clean old data first) ────────────
        logging.info("[Ingest] Step 5/5 — Uploading to Azure...")
        delete_document_blobs(document_id)
        delete_document_chunks(document_id)
        for section in sections:
            upload_parent_section(section)
        upsert_chunks(all_chunks)

        logging.info(
            f"[Ingest] Done — '{document_title}' ingested successfully "
            f"({len(sections)} sections, {len(all_chunks)} chunks)"
        )

        return func.HttpResponse(
            f"Success: ingested {file_name} "
            f"({len(sections)} sections, {len(all_chunks)} chunks)",
            status_code=200,
        )

    except Exception as e:
        logging.exception(f"[Ingest] Failed to process {file_name}: {e}")
        return func.HttpResponse(
            f"Error processing {file_name}: {str(e)}",
            status_code=500,
        )


@app.route(route="sharepoint_delete", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def sharepoint_delete(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete all indexed data for a document removed from SharePoint.

    Expected JSON body:
    {
        "event": "delete",
        "fileId": "123"
    }
    """
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    file_id = body.get("fileId")
    if not file_id:
        return func.HttpResponse("Missing required field: fileId", status_code=400)

    logging.info(f"[Delete] Removing all data for fileId={file_id}")

    try:
        document_id = file_id
        delete_document_chunks(document_id)
        delete_document_blobs(document_id)

        logging.info(f"[Delete] Done — all data for fileId={file_id} removed")
        return func.HttpResponse(
            f"Success: deleted all data for fileId={file_id}",
            status_code=200,
        )

    except Exception as e:
        logging.exception(f"[Delete] Failed to delete fileId={file_id}: {e}")
        return func.HttpResponse(
            f"Error deleting fileId={file_id}: {str(e)}",
            status_code=500,
        )
