import os

from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "true"

BASE_DIR =  Path(__file__).resolve().parent.parent.parent
MSA_DIR = Path(BASE_DIR) / "data" / "contracts"
INDEX_NAME = "llama-text-embed-v2-index"
NAMESPACE = "contracts"

def build_vector_databses():
    load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("PINECONE_API_KEY")

    if not api_key:
        raise ValueError("PINECONE_API_KEY is missing from your .env file")

    index = Pinecone(api_key=api_key).Index(INDEX_NAME)

    print(f"Loading Markdown contracts from {MSA_DIR}")

    # Loading MSA files
    all_documents = []

    if not MSA_DIR.exists():
        print(f"Error: Contract directory not found at {MSA_DIR}")
        return

    for file in MSA_DIR.glob('*.md'):
        print(f"Processing contract: {file.name}")
        raw_text = file.read_text(encoding = 'utf-8')
        vendor = file.stem.split('_')[0]

        doc = Document(
            page_content = raw_text,
            metadata = {
                "source" : file.name,
                "vendor" : vendor
            }
        )
        all_documents.append(doc)

    # Using RecursiveCharacterTextSplitter to split the text with overlaps
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50,
    )

    # Chunking
    chunks = text_splitter.split_documents(all_documents)
    print(f"Split {len(all_documents)} documents into {len(chunks)} chunks.")

    records = []
    chunk_numbers = {}
    for chunk in chunks:
        source = chunk.metadata["source"]
        chunk_number = chunk_numbers.get(source, 0)
        chunk_numbers[source] = chunk_number + 1
        chunk_id = f"{source}-chunk-{chunk_number}"

        records.append({
            "_id": chunk_id,
            "text": chunk.page_content,
            "source": source,
            "vendor": chunk.metadata["vendor"],
        })

    # 96 is Pinecone's batch limit for indexes with integrated embeddings.
    for start in range(0, len(records), 96):
        index.upsert_records(
            namespace=NAMESPACE,
            records=records[start:start + 96],
        )

    print(f"Uploaded {len(records)} chunks to Pinecone index '{INDEX_NAME}'.")


if __name__ == '__main__':
    build_vector_databses()
