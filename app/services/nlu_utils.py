"""Utility functions for NLU, including yes/no extraction from Tamil text."""

import re
from typing import Optional


def extract_yes_no_from_tamil(text: str) -> Optional[str]:
    """
    Extract yes/no response from Tamil text.
    
    Args:
        text: Tamil text input
        
    Returns:
        "yes", "no", or None if unclear
    """
    text_lower = text.lower().strip()
    
    # Tamil yes patterns (including partial/misrecognized forms)
    yes_patterns = [
        r"ஆம்",
        r"அம்",  # Partial/misrecognized "ஆம்"
        r"உண்டு",
        r"இருக்கிறது",
        r"இருக்கும்",
        r"வேண்டும்",
        r"சரி",
        r"ஆகும்",
        r"உள்ளது",
        r"உள்ள",  # Partial
    ]
    
    # Tamil no patterns
    no_patterns = [
        r"இல்லை",
        r"இல்லாது",
        r"இல்ல",
        r"வேண்டாம்",
        r"சரியில்லை",
    ]
    
    # Check for yes
    for pattern in yes_patterns:
        if re.search(pattern, text_lower):
            return "yes"
    
    # Check for no
    for pattern in no_patterns:
        if re.search(pattern, text_lower):
            return "no"
    
    # Check for English yes/no (fallback)
    if re.search(r"\b(yes|yeah|yep|y|ok|okay|sure)\b", text_lower):
        return "yes"
    if re.search(r"\b(no|nope|nah|n)\b", text_lower):
        return "no"
    
    return None

