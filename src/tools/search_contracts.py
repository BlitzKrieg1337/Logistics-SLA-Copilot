from langchain_core.tools import tool
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone, SearchQuery
import os


BASE_DIR = Path(__file__).resolve().parent.parent.parent

INDEX_NAME = "llama-text-embed-v2-index"
NAMESPACE = "contracts"


load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("PINECONE_API_KEY")

if not api_key:
    raise ValueError("PINECONE_API_KEY is missing from your .env file")

pc = Pinecone(api_key=api_key)
index = pc.Index(INDEX_NAME)


@tool
def search_contracts(query: str, vendor_name: str) -> str:
    """
    Search the vendor's legal Master Service Agreement (MSA) for
    Service Level Agreements (SLAs), grace periods, and financial
    penalty clauses.
    """

    try:
        search_query = SearchQuery(
        inputs={"text": query},
        top_k=4,
        filter={"vendor": vendor_name})

        results = index.search(
            namespace=NAMESPACE,
            query=search_query,
        )

        hits = results.result.hits

        if not hits:
            return f"No SLA or contract documentation found for vendor: {vendor_name}"

        context = []

        for hit in hits:
            fields = hit.fields

            context.append(
                f"[Source: {fields.get('source', 'Unknown')}]\n"
                f"{fields.get('text', '')}"
            )

        return "\n\n".join(context)

    except Exception as e:
        return f"Error -> {e}"


if __name__ == "__main__":
    print(
        search_contracts.invoke({
            "query": "What is the penalty for late delivery?",
            "vendor_name": "Tata"
        })
    )