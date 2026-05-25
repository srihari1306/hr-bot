from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
import os


def extract_structure(file_path: str) -> dict:
    """Extract structured content from a PDF using Azure Document Intelligence."""
    client = DocumentIntelligenceClient(
        endpoint=os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"])
    )
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=f,
            content_type="application/octet-stream"
        )
    result = poller.result()

    # Build structured output: list of {type, content, level, page}
    elements = []
    for para in result.paragraphs or []:
        role = para.role or "paragraph"
        level = None
        if role in ("title", "sectionHeading"):
            # Map heading levels: title→H1, sectionHeading→H2
            level = 1 if role == "title" else 2
        elements.append({
            "type": "heading" if level else "paragraph",
            "level": level,
            "content": para.content,
            "page": para.bounding_regions[0].page_number if para.bounding_regions else 1
        })

    for table in result.tables or []:
        rows = []
        headers = []
        for cell in table.cells:
            if cell.row_index == 0:
                headers.append(cell.content)
            else:
                while len(rows) <= cell.row_index - 1:
                    rows.append([])
                while len(rows[cell.row_index - 1]) <= cell.column_index:
                    rows[cell.row_index - 1].append("")
                rows[cell.row_index - 1][cell.column_index] = cell.content

        # Format as text: header row + data rows
        table_text = " | ".join(headers) + "\n"
        for row in rows:
            table_text += " | ".join(row) + "\n"

        elements.append({
            "type": "table",
            "level": None,
            "content": table_text,
            "headers": headers,
            "page": table.bounding_regions[0].page_number if table.bounding_regions else 1
        })

    return {"elements": elements}
