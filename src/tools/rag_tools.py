from langchain_core.tools import tool
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTOR_DIR = Path.joinpath(BASE_DIR, "data", "vector_store")

emb_model = HuggingFaceEmbeddings(model_name = "all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory = str(VECTOR_DIR), embedding_function = emb_model)

@tool
def ragsearch(query: str, vendor_name: str) -> str:
    """
    Search the vendor's legal Master Service Agreement (MSA) for Service Level Agreements (SLAs), 
    grace periods, and financial penalty clauses.
    
    Args:
        query: The specific legal or penalty question (e.g., "What is the penalty for late delivery?")
        vendor_name: The exact name of the vendor (e.g., "Siemens", "Dell", "Tata", "Cisco")
    """

    try:
        retriever = vector_db.as_retriever(search_kwargs = { "k" : 4 , "filter" : {"vendor" : vendor_name}})
        docs = retriever.invoke(query)

        if not docs:
            return f"No SLA or contract documentation found for vendor: {vendor_name}"

        context = "\n\n".join([
            f"[Source : {doc.metadata.get('source', 'Unknown')}]\n{doc.page_content}" for doc in docs
        ])

        return context

    except Exception as e:
        return f"Error -> {e}"


# if __name__ == "__main__":
    # FOR TESTING
    # print(ragsearch("What is the penalty?", "Tata"))