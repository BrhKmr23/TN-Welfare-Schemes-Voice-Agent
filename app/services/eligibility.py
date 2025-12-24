"""Deterministic eligibility engine for welfare schemes.

This module evaluates eligibility rules and returns matching schemes.
No memory, no planner, no voice - pure evaluation only.
"""

import json
import os
from typing import Any, Dict, List, Optional


def load_schemes() -> List[Dict[str, Any]]:
    """Load schemes from schemes.json file."""
    # Get path to schemes.json (in app/ directory, one level up from services/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    schemes_path = os.path.join(app_dir, "schemes.json")
    
    with open(schemes_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("schemes", [])


def evaluate_rule(rule: Dict[str, Any], slots: Dict[str, Any]) -> bool:
    """
    Evaluate a single eligibility rule against slot values.
    
    Supported operators:
    - == : equality
    - >= : greater than or equal
    - <= : less than or equal
    - between : value is between two numbers (rule.value must be [min, max])
    
    Returns:
        True if rule passes, False otherwise.
    """
    field = rule.get("field")
    operator = rule.get("operator")
    expected_value = rule.get("value")
    
    if field not in slots:
        return False
    
    actual_value = slots[field]
    
    # If actual value is None, rule fails (missing data)
    if actual_value is None:
        return False
    
    if operator == "==":
        return actual_value == expected_value
    
    elif operator == ">=":
        return actual_value >= expected_value
    
    elif operator == "<=":
        return actual_value <= expected_value
    
    elif operator == "between":
        # expected_value should be [min, max]
        if not isinstance(expected_value, list) or len(expected_value) != 2:
            return False
        min_val, max_val = expected_value
        return min_val <= actual_value <= max_val
    
    else:
        # Unknown operator - fail safely
        return False


def check_scheme_eligibility(
    scheme: Dict[str, Any], slots: Dict[str, Any]
) -> Optional[Dict[str, str]]:
    """
    Check if a scheme is eligible based on slots.
    
    Returns:
        Dict with scheme_id and reason_ta if eligible, None otherwise.
    """
    eligibility = scheme.get("eligibility", {})
    required_fields = eligibility.get("required_fields", [])
    rules = eligibility.get("rules", [])
    
    # Check if all required fields are present and not None
    for field in required_fields:
        if field not in slots or slots[field] is None:
            # Missing required field - do not evaluate this scheme
            return None
    
    # Evaluate all rules (AND logic - all must pass)
    for rule in rules:
        if not evaluate_rule(rule, slots):
            # Rule failed - not eligible
            return None
    
    # All rules passed - eligible
    return {
        "scheme_id": scheme["scheme_id"],
        "reason_ta": eligibility.get("reason_ta", ""),
    }


def check_eligibility(slots: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Main eligibility engine function.
    
    Input:
        slots: Dict of slot_name -> value (e.g., {"age": 65, "bpl_status": True})
    
    Output:
        List of eligible schemes, each with scheme_id and reason_ta.
        Empty list if no schemes match.
 
    """
    schemes = load_schemes()
    eligible = []
    
    for scheme in schemes:
        result = check_scheme_eligibility(scheme, slots)
        if result:
            eligible.append(result)
    
    return eligible

