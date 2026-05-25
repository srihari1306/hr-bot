from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
    HnswParameters, VectorSearchProfile, SemanticConfiguration,
    SemanticSearch, SemanticPrioritizedFields, SemanticField
)
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import os

load_dotenv()

client = SearchIndexClient(
    endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
    credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"])
)

fields = [
    SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
    SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="section_id", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="section_heading", type=SearchFieldDataType.String),
    SearchableField(name="document_title", type=SearchFieldDataType.String),
    SimpleField(name="page_number", type=SearchFieldDataType.Int32),
    SimpleField(name="source_url", type=SearchFieldDataType.String),
    SimpleField(name="chunk_type", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=3072,
        vector_search_profile_name="hnsw-profile"
    )
]

vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(
        name="hnsw-algo",
        parameters=HnswParameters(m=4, ef_construction=400)
    )],
    profiles=[VectorSearchProfile(
        name="hnsw-profile",
        algorithm_configuration_name="hnsw-algo"
    )]
)

semantic_config = SemanticConfiguration(
    name="hr-semantic",
    prioritized_fields=SemanticPrioritizedFields(
        content_fields=[SemanticField(field_name="content")],
        keywords_fields=[SemanticField(field_name="section_heading")]
    )
)

index = SearchIndex(
    name=os.environ["AZURE_SEARCH_INDEX_NAME"],
    fields=fields,
    vector_search=vector_search,
    semantic_search=SemanticSearch(configurations=[semantic_config])
)

client.create_or_update_index(index)
print("Index created.")
