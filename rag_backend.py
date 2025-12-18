import os
import json
import logging
import numpy as np
from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Hardcode API keys and URLs (you can also use env vars)
QDRANT_URL = os.getenv("QDRANT_URL", "http://49.50.117.66:6333")
# QDRANT_URL = os.getenv("QDRANT_URL", "http://10.0.3.20:6333")
QDRANT_KEY = os.getenv("QDRANT_KEY", "3mUpK_yp6N6YFourp_EjasB76m_YedpMllvbn80Yhbw")
OPENAI_API_KEY = os.getenv("RAG_OPENAI_API_KEY", "asfs")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://bge-m3-inference.serve.cyfuture.ai/openai/v1")
EMBEDDING_MODEL = "bge-m3"

# Check for required configuration
if not all([QDRANT_KEY, QDRANT_URL, OPENAI_API_KEY]):
    logger.warning("Missing RAG configuration: QDRANT_KEY, QDRANT_URL, or RAG_OPENAI_API_KEY")

# Initialize the OpenAI client for embeddings
oai_client = OpenAI(
    base_url=EMBEDDING_BASE_URL,
    api_key=OPENAI_API_KEY
)

# Custom VectorStoreRetriever
class VectorStoreRetriever:
    def __init__(self, docs: list, vectors: list, oai_client):
        self._arr = np.array(vectors)
        self._docs = docs
        self._client = oai_client

    @classmethod
    @retry(stop=stop_after_attempt(7), wait=wait_exponential(multiplier=1, min=4, max=30))
    def from_docs(cls, docs, oai_client):
        try:
            embeddings = oai_client.embeddings.create(
                model=EMBEDDING_MODEL, input=[doc.page_content for doc in docs]
            )
            vectors = [emb.embedding for emb in embeddings.data]
            return cls(docs, vectors, oai_client)
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(7), wait=wait_exponential(multiplier=1, min=4, max=30))
    def query(self, query: str, k: int = 3) -> list[dict]:
        try:
            if self._arr.size == 0 or len(self._docs) == 0:
                logger.warning("Query attempted but no documents available in retriever.")
                return []

            # Ensure k is sensible
            n = len(self._docs)
            if k <= 0:
                logger.warning("k <= 0 in query(); defaulting k=1")
                k = 1
            if k > n:
                logger.info(f"k ({k}) is greater than number of docs ({n}); clamping k to {n}.")
                k = n

            # get embedding for the query
            embed = self._client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
            q_vec = np.array(embed.data[0].embedding)

            # compute cosine-like score: dot product (works if vectors are normalized)
            scores = q_vec @ self._arr.T  # shape: (n,)

            # pick top-k indices robustly
            if k == n:
                top_k_idx_sorted = np.argsort(-scores)
            else:
                top_k_idx = np.argpartition(scores, -k)[-k:]
                top_k_idx_sorted = top_k_idx[np.argsort(-scores[top_k_idx])]

            results = []
            for idx in top_k_idx_sorted:
                results.append({
                    **(self._docs[idx].metadata or {}),
                    "content": self._docs[idx].page_content,
                    "similarity": float(scores[idx])
                })
            return results

        except Exception as e:
            logger.error(f"Error querying retriever: {str(e)}")
            logger.debug("Full exception:", exc_info=True)
            return [{"error": f"Failed to query retriever: {str(e)}"}]


# Document processing function
def preprocess_documents(file_paths: List[str]) -> List:
    """
    Process text files into document chunks for Qdrant.
    
    Args:
        file_paths (List[str]): List of paths to text files.
    
    Returns:
        List: Split document chunks ready for vector storage.
    """
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=700,
        chunk_overlap=50,
        disallowed_special=()
    )
    all_splits = []
    for file_path in file_paths:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            continue
        if not os.path.isfile(file_path):
            logger.warning(f"Path is not a file: {file_path}")
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    logger.warning(f"File is empty: {file_path}")
                    continue
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
            splits = text_splitter.split_documents(documents)
            all_splits.extend(splits)
            logger.info(f"Successfully processed file: {file_path}")
        except PermissionError as e:
            logger.error(f"Permission denied for {file_path}: {str(e)}")
        except UnicodeDecodeError as e:
            logger.error(f"Invalid file format for {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading {file_path}: {str(e)}")
    if not all_splits:
        logger.error("No valid documents processed from provided file paths.")
    return all_splits

# Create Qdrant vector store
@retry(stop=stop_after_attempt(7), wait=wait_exponential(multiplier=1, min=4, max=30))
def create_vector_store(doc_splits: List, collection_name: str = "sales_knowledge_base") -> VectorStoreRetriever:
    """
    Create a Qdrant vector store and retriever from document splits.
    
    Args:
        doc_splits (List): List of document chunks.
        collection_name (str): Name of the Qdrant collection.
    
    Returns:
        VectorStoreRetriever: Configured retriever.
    """
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, timeout=120,prefer_grpc=False)
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
            logger.info(f"Deleted existing Qdrant collection: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1024, distance="Cosine")
        )
        retriever = VectorStoreRetriever.from_docs(doc_splits, oai_client)
        
        points = [
            PointStruct(
                id=idx,
                vector=vector,
                payload={"content": doc.page_content, "metadata": doc.metadata}
            )
            for idx, (doc, vector) in enumerate(zip(doc_splits, retriever._arr))
        ]
        client.upsert(collection_name=collection_name, points=points)
        logger.info(f"Created Qdrant vector store: {collection_name}")
        return retriever
    except Exception as e:
        logger.error(f"Failed to create Qdrant vector store: {str(e)}")
        raise
    
# Define the RAG retriever function
def rag_retriever(query: str, vector_store: Optional[VectorStoreRetriever], k: int = 3) -> str:
    """
    Retrieve relevant document chunks from the Qdrant vector store for a given query.
    
    Args:
        query (str): The user's query to search the vector store.
        vector_store (VectorStoreRetriever): The initialized vector store retriever.
        k (int): Number of top results to return.
    
    Returns:
        str: JSON string containing retrieved document contents and metadata.
    """
    if not vector_store:
        logger.error("Vector store not initialized.")
        return json.dumps({"error": "Knowledge base not initialized. Please upload documents first."})
    
    try:
        results = vector_store.query(query, k=k)
        logger.info(f"Retrieved {len(results)} documents for query: {query}")
        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Error retrieving documents for query '{query}': {str(e)}")
        return json.dumps({"error": f"Failed to retrieve documents: {str(e)}"})

      



# =========================================
# MAIN RUNNER + QUERY TESTER (USE THIS)
# =========================================

# if __name__ == "__main__":
#     import sys
#     import json
#     from pathlib import Path

#     print("\n=== RAG DOCUMENT LOADING ===")
#     paths = input("Enter file paths (comma separated): ").strip()
#     file_paths = [str(Path(p.strip()).expanduser()) for p in paths.split(",")]

#     print("\nProcessing documents...")
#     doc_splits = preprocess_documents(file_paths)
#     print(f"Document chunks: {len(doc_splits)}")

#     if not doc_splits:
#         print("No valid documents. Exiting.")
#         sys.exit(1)

#     print("\nCreating vector store...")
#     retriever = create_vector_store(doc_splits, "test_rag_collection")
#     print("Vector store ready!")

#     # ============================
#     # RAG QUERY TEST MODE
#     # ============================
#     print("\n=== RAG QUERY TEST MODE ===")
#     print("Type your question. Type 'exit' to quit.\n")

#     while True:
#         query = input("Query > ").strip()
#         if query.lower() in ("exit", "quit"):
#             print("Exiting.")
#             break

#         results = retriever.query(query, k=5)
#         print(f"\nTop {len(results)} results:\n")

#         for i, r in enumerate(results, start=1):
#             print(f"--- Result #{i} ---")
#             print("Similarity:", r.get("similarity"))
#             print("Content:", r.get("content", "")[:300].replace("\n", " "), "...\n")

#         print("----------------------------------\n")
