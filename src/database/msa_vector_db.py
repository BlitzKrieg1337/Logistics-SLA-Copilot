

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR =  Path(__file__).resolve().parent.parent.parent
MSA_DIR = Path(BASE_DIR) / "data" / "contracts"
VECTOR_DB = Path(BASE_DIR) / "data" / "vector_store"

def build_vector_databse():
    print(f"Loading Markdown contracts from {MSA_DIR}")

    all_documents = []
        
    for file in MSA_DIR.glob('*.md'):
        print(f"Processing contract: {file.name}")
        raw_text = file.read_text(encoding = 'utf-8')
        all_documents.append(raw_text)

    text_spltter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50,
    )

    chunks = text_spltter.create_documents(all_documents)
    print(f"Split {len(all_documents)} documents into {len(chunks)} chunks.")

if __name__ == '__main__':
    build_vector_databse()
