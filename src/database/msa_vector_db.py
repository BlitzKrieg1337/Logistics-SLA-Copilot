import shutil

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR =  Path(__file__).resolve().parent.parent.parent
MSA_DIR = Path(BASE_DIR) / "data" / "contracts"
VECTOR_DB = Path(BASE_DIR) / "data" / "vector_store"

def build_vector_databse():
    print(f"Loading Markdown contracts from {MSA_DIR}")

    # Loading MSA files
    all_documents = []

    for file in MSA_DIR.glob('*.md'):
        print(f"Processing contract: {file.name}")
        raw_text = file.read_text(encoding = 'utf-8')
        all_documents.append(raw_text)

    # Using RecursiveCharacterTextSplitter to split the text with overlaps
    text_spltter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50,
    )

    # Chunking
    chunks = text_spltter.create_documents(all_documents)
    print(f"Split {len(all_documents)} documents into {len(chunks)} chunks.")

    # Importing Embedding
    print(f"Importing Embedding model")
    emb_model =  HuggingFaceEmbeddings(model_name = "all-MiniLM-L6-v2")

    # Creating the Vector Database
    try:
        # Remove if already exits
        if VECTOR_DB.exists():
            shutil.rmtree(VECTOR_DB)

        Chroma.from_documents(
            documents = chunks,
            embedding = emb_model,
            persist_directory = str(VECTOR_DB)
        )
        print(f"Created Vector Database successfully at {VECTOR_DB}!")
    except Exception as e:
        print(f"Error creating Vector Database -> {e}")



if __name__ == '__main__':
    build_vector_databse()
