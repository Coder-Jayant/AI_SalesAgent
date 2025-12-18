"""
rag_manager.py
RAG state and collection management
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# RAG State file
RAG_STATE_FILE = os.getenv("RAG_STATE_FILE", "rag_state.json")

# Global RAG state (module-level)
RAG_COLLECTIONS: Dict[str, Any] = {}  # Maps collection names to retrievers
ACTIVE_COLLECTION: Optional[str] = None  # Currently active collection name


def _load_rag_state() -> Dict[str, Any]:
    """Load RAG state from file."""
    try:
        p = Path(RAG_STATE_FILE)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"active_collection": None}
    except Exception as e:
        logger.warning(f"Failed to load RAG state: {e}")
        return {"active_collection": None}


def _save_rag_state(state: Dict[str, Any]):
    """Save RAG state to file."""
    try:
        Path(RAG_STATE_FILE).write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to save RAG state: {e}")


def get_active_collection() -> Optional[str]:
    """Get the currently active RAG collection."""
    global ACTIVE_COLLECTION
    if ACTIVE_COLLECTION:
        return ACTIVE_COLLECTION
    state = _load_rag_state()
    ACTIVE_COLLECTION = state.get("active_collection")
    return ACTIVE_COLLECTION


def set_active_collection(collection_name: Optional[str]):
    """Set the active RAG collection."""
    global ACTIVE_COLLECTION
    ACTIVE_COLLECTION = collection_name
    state = _load_rag_state()
    state["active_collection"] = collection_name
    _save_rag_state(state)
    logger.info(f"Active collection set to: {collection_name}")


def get_collection_retriever(collection_name: str) -> Optional[Any]:
    """Get cached retriever for a collection."""
    global RAG_COLLECTIONS
    return RAG_COLLECTIONS.get(collection_name)


def set_collection_retriever(collection_name: str, retriever: Any):
    """Cache retriever for a collection."""
    global RAG_COLLECTIONS
    RAG_COLLECTIONS[collection_name] = retriever
    logger.info(f"Cached retriever for collection: {collection_name}")


def clear_collection_cache(collection_name: Optional[str] = None):
    """Clear cached retriever(s)."""
    global RAG_COLLECTIONS
    if collection_name:
        if collection_name in RAG_COLLECTIONS:
            del RAG_COLLECTIONS[collection_name]
            logger.info(f"Cleared cache for collection: {collection_name}")
    else:
        RAG_COLLECTIONS.clear()
        logger.info("Cleared all collection caches")


