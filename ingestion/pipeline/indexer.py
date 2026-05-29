import logging
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from schemas.models import ChildChunk


def get_search_client():
    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name=os.environ["AZURE_SEARCH_INDEX_NAME"],
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"])
    )


def upsert_chunks(chunks: list[ChildChunk]):
    """Upsert child chunks to Azure AI Search index."""
    client = get_search_client()
    docs = [
        {
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "section_id": c.section_id,
            "section_heading": c.section_heading,
            "document_title": c.document_title,
            "page_number": c.page_number,
            "source_url": c.source_url,
            "content": c.content,
            "content_vector": c.content_vector,
            "chunk_type": c.chunk_type
        }
        for c in chunks
    ]
    # Batch upload in groups of 1000
    for i in range(0, len(docs), 1000):
        client.upload_documents(docs[i:i + 1000])
    logging.info(f"Indexed {len(docs)} chunks.")


def delete_document_chunks(document_id: str):
    """Delete all chunks for a given document from the search index."""
    client = get_search_client()
    results = client.search(
        search_text="*",
        filter=f"document_id eq '{document_id}'",
        select=["chunk_id"]
    )
    ids = [{"chunk_id": r["chunk_id"]} for r in results]
    if ids:
        client.delete_documents(ids)
    logging.info(f"Deleted {len(ids)} old chunks for document {document_id}.")
