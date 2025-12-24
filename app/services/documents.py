"""Document readiness checking for welfare schemes."""

import json
import os
from typing import Any, Dict, List, Optional


def load_schemes() -> List[Dict[str, Any]]:
    """Load schemes from schemes.json file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    schemes_path = os.path.join(app_dir, "schemes.json")
    
    with open(schemes_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("schemes", [])


def get_required_documents(scheme_id: str) -> List[str]:
    """
    Get list of required documents for a scheme.
    
    Args:
        scheme_id: Scheme ID (e.g., "CEN_IGNOAPS_001")
    
    Returns:
        List of document names (e.g., ["aadhaar", "ration_card", ...])
    """
    schemes = load_schemes()
    for scheme in schemes:
        if scheme.get("scheme_id") == scheme_id:
            return scheme.get("required_documents", [])
    return []


def initialize_document_state(scheme_id: str) -> Dict[str, str]:
    """
    Initialize document state with all documents set to "unknown".
    
    Args:
        scheme_id: Scheme ID
    
    Returns:
        Dict mapping document names to "unknown"
    """
    required_docs = get_required_documents(scheme_id)
    return {doc: "unknown" for doc in required_docs}


def get_next_unknown_document(documents: Dict[str, str]) -> Optional[str]:
    """
    Get the first document that is still "unknown".
    
    Args:
        documents: Document state dict
    
    Returns:
        Document name if found, None if all are known
    """
    for doc, status in documents.items():
        if status == "unknown":
            return doc
    return None


def check_document_readiness(documents: Dict[str, str]) -> Dict[str, str]:
    """
    Check document readiness status.
    
    Returns:
        Dict with keys:
        - "status": "ready" | "missing" | "checking"
        - "missing_docs": List of documents with status "no"
        - "next_doc": Next document to ask about (if status is "checking")
    """
    unknown_docs = [doc for doc, status in documents.items() if status == "unknown"]
    missing_docs = [doc for doc, status in documents.items() if status == "no"]
    
    if unknown_docs:
        return {
            "status": "checking",
            "missing_docs": [],
            "next_doc": unknown_docs[0],
        }
    elif missing_docs:
        return {
            "status": "missing",
            "missing_docs": missing_docs,
            "next_doc": None,
        }
    else:
        return {
            "status": "ready",
            "missing_docs": [],
            "next_doc": None,
        }

