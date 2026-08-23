from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}

# TODO: Write a tool to read a doc
@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document.",
)
def read_document(doc_id: str=Field(description="The ID of the document to read.")) -> str:
    if doc_id not in docs:
        raise ValueError(f"Document with ID '{doc_id}' not found.")
    return docs[doc_id]

# TODO: Write a tool to edit a doc

@mcp.tool(
    name="edit_doc_contents",
    description="Edit the contents of a document.",
)

def edit_document(doc_id: str=Field(description="The ID of the document to edit."), old_contents: str=Field(description="The text to be replaced. Must exactly match including whitespace."), new_contents: str=Field(description="The new text to insert in place of the old text.")):
    if doc_id not in docs:
        raise ValueError(f"Document with ID '{doc_id}' not found.")
    docs[doc_id] = docs[doc_id].replace(old_contents, new_contents)
    return f"Document '{doc_id}' updated successfully."

# TODO: Write a resource to return all doc id's
@mcp.resource(
    "docs://documents",
    mime_type="application/json"
)
def list_documents()-> list[str]:
    return list(docs.keys())

# TODO: Write a resource to return the contents of a particular doc
@mcp.resource(
    "docs://documents/{doc_id}",
    mime_type="text/plain"
)
def get_document_contents(doc_id: str) -> str:
    if doc_id not in docs:
        raise ValueError(f"Document with ID '{doc_id}' not found.")
    return docs[doc_id]

# TODO: Write a prompt to rewrite a doc in markdown format
@mcp.prompt(
    name="format",
    description="Rewrite a document in markdown format.",
)
def format_document(doc_id: str=Field(description="The ID of the document to format.")) -> list[base.UserMessage]:
    if doc_id not in docs:
        raise ValueError(f"Document with ID '{doc_id}' not found.")
    # Placeholder for actual formatting logic
    prompt_text = f"""
Your goal is to reformat a document to be written with markdown syntax.

The id of the document you need to reformat is:

{doc_id}


Add in headers, bullet points, tables, etc as necessary. Feel free to add in extra formatting.
Use the 'edit_document' tool to edit the document. After the document has been reformatted...
"""
    # Return it wrapped as a UserMessage so the client knows how to handle it.

    return [
        base.UserMessage(prompt_text)
    ]
# TODO: Write a prompt to summarize a doc


if __name__ == "__main__":
    mcp.run(transport="stdio")
