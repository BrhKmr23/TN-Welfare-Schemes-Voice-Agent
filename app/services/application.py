"""Mock application submission for welfare schemes."""

import random
import string
from typing import Any, Dict


def generate_application_id() -> str:
    """Generate a mock application ID."""
    prefix = "TN-APP-"
    suffix = "".join(random.choices(string.digits, k=5))
    return f"{prefix}{suffix}"


def apply_for_scheme(
    scheme_id: str,
    user_profile: Dict[str, Any],
) -> Dict[str, str]:
    """
    Mock application submission tool.
    
    Args:
        scheme_id: Scheme ID (e.g., "CEN_IGNOAPS_001")
        user_profile: User slots/profile data
    
    Returns:
        Dict with:
        - "status": "submitted" | "failed"
        - "application_id": Application ID if successful
        - "message": Status message
    """
    # Mock validation (always succeeds in mock)
    # In real system, this would validate documents, check duplicates, etc.
    
    application_id = generate_application_id()
    
    return {
        "status": "submitted",
        "application_id": application_id,
        "message": "Application submitted successfully",
    }

