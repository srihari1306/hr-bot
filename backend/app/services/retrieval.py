import os
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential


def get_search_client():
    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name=os.environ["AZURE_SEARCH_INDEX_NAME"],
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"])
    )


async def retrieve_chunks(query: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
    """Hybrid search: vector + semantic over Azure AI Search. Returns deduplicated chunks by section."""
    client = get_search_client()

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=10,
        fields="content_vector"
    )

    results = client.search(
        search_text=query,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name="hr-semantic",
        query_caption="extractive",
        query_answer="extractive",
        select=["chunk_id", "document_id", "section_id", "section_heading",
                "document_title", "content", "source_url", "chunk_type", "page_number"],
        top=10
    )

    chunks = []
    seen_section_ids = set()

    for r in results:
        chunk = dict(r)
        section_id = chunk.get("section_id")
        if section_id not in seen_section_ids:
            seen_section_ids.add(section_id)
            chunks.append(chunk)
        if len(chunks) >= top_k:
            break

    return chunks
