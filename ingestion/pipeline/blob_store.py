import json
import os
from azure.storage.blob import BlobServiceClient
from schemas.models import ParentSection

_client = None


def get_blob_client():
    global _client
    if not _client:
        _client = BlobServiceClient.from_connection_string(
            os.environ["AZURE_BLOB_CONNECTION_STRING"]
        )
    return _client


def upload_parent_section(section: ParentSection):
    """Upload a parent section as JSON to Azure Blob Storage."""
    container = os.environ["AZURE_BLOB_CONTAINER"]
    blob_path = f"documents/{section.document_id}/sections/{section.section_id}.json"
    client = get_blob_client()
    blob = client.get_blob_client(container=container, blob=blob_path)
    blob.upload_blob(json.dumps({
        "document_id": section.document_id,
        "section_id": section.section_id,
        "heading": section.heading,
        "full_text": section.full_text,
        "page_range": list(section.page_range),
        "source_url": section.source_url
    }), overwrite=True)


def fetch_parent_section(document_id: str, section_id: str) -> dict | None:
    """Fetch a parent section from Azure Blob Storage."""
    try:
        container = os.environ["AZURE_BLOB_CONTAINER"]
        blob_path = f"documents/{document_id}/sections/{section_id}.json"
        client = get_blob_client()
        blob = client.get_blob_client(container=container, blob=blob_path)
        data = blob.download_blob().readall()
        return json.loads(data)
    except Exception:
        return None


def delete_document_blobs(document_id: str):
    """Delete all parent section blobs for a document."""
    container = os.environ["AZURE_BLOB_CONTAINER"]
    client = get_blob_client()
    container_client = client.get_container_client(container)
    prefix = f"documents/{document_id}/sections/"
    for blob in container_client.list_blobs(name_starts_with=prefix):
        container_client.delete_blob(blob.name)
