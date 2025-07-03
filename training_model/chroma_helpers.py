import os
import mimetypes
from django.conf import settings
from langchain_community.document_loaders import (
    CSVLoader,
    UnstructuredWordDocumentLoader,
    PyPDFLoader,
)
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings as ChromaSettings

OPENAI_API_KEY = settings.OPENAI_API_KEY
BASE_DIR = settings.BASE_DIR
MODELS_DIR = os.path.join(BASE_DIR, "models", "chroma")

# Ensure the ChromaDB directory exists
os.makedirs(MODELS_DIR, exist_ok=True)

# ChromaDB client configuration
chroma_client = chromadb.PersistentClient(
    path=MODELS_DIR,
    settings=ChromaSettings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)


def get_loader(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type == "application/pdf":
        return PyPDFLoader(file_path)
    elif mime_type == "text/csv":
        return CSVLoader(file_path)
    elif mime_type in [
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        return UnstructuredWordDocumentLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")


def build_or_update_chroma_index(file_path, index_name):
    """
    Build or update ChromaDB index with documents
    """
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    loader = get_loader(file_path)
    pages = loader.load_and_split()
    
    # Create or get existing collection
    collection_name = f"collection_{index_name}"
    
    try:
        # Try to get existing collection
        chroma_db = Chroma(
            client=chroma_client,
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=MODELS_DIR
        )
        
        # Add new documents to existing collection
        print(f"Updating ChromaDB collection: {collection_name}")
        chroma_db.add_documents(pages)
        
    except Exception as e:
        # Create new collection if it doesn't exist
        print(f"Creating new ChromaDB collection: {collection_name}")
        chroma_db = Chroma.from_documents(
            documents=pages,
            embedding=embeddings,
            client=chroma_client,
            collection_name=collection_name,
            persist_directory=MODELS_DIR
        )
    
    # Persist the changes
    chroma_db.persist()
    
    return chroma_db


def get_chroma_index(index_name):
    """
    Load existing ChromaDB index
    """
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    collection_name = f"collection_{index_name}"
    
    try:
        chroma_db = Chroma(
            client=chroma_client,
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=MODELS_DIR
        )
        return chroma_db
    except Exception as e:
        print(f"Failed to load ChromaDB collection {collection_name}: {e}")
        return None
