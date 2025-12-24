from dataclasses import asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.agent_state import AgentState, SLOT_NAMES


class PlannerAction(str, Enum):
    ASK_MISSING_SLOT = "ASK_MISSING_SLOT"
    HANDLE_CONTRADICTION = "HANDLE_CONTRADICTION"
    CHECK_ELIGIBILITY = "CHECK_ELIGIBILITY"
    CHECK_DOCUMENTS = "CHECK_DOCUMENTS"
    CONFIRM_APPLICATION = "CONFIRM_APPLICATION"
    APPLY_SCHEME = "APPLY_SCHEME"
    RESPOND_RESULT = "RESPOND_RESULT"
    REPEAT_INPUT = "REPEAT_INPUT"


SCHEME_REQUIRED_SLOTS: Dict[str, List[str]] = {
    # IGNOAPS: Indira Gandhi National Old Age Pension Scheme
    "IGNOAPS": ["age", "bpl_status"],
    # PM-KISAN: Pradhan Mantri Kisan Samman Nidhi
    "PM-KISAN": ["is_landholding_farmer", "not_excluded_category"],
    # PMMVY: Pradhan Mantri Matru Vandana Yojana
    "PMMVY": [
        "is_pregnant_or_lactating",
        "meets_any_social_category",
        "age_at_childbirth",  # logically derived from "age" but kept explicit per spec text
    ],
}


def get_candidate_schemes(state: AgentState) -> List[str]:
    """
    Stage 1: Narrow down candidate schemes based on already known slots.
    
    This prevents asking irrelevant questions (e.g., asking a 65-year-old male
    if they are pregnant).
    
    Returns:
        List of scheme names that are still viable given current slot values.
    """
    candidates = []
    
    # IGNOAPS: Old Age Pension - requires age >= 60
    age = state.slots.get("age")
    if age is not None and age >= 60:
        candidates.append("IGNOAPS")
    
    # PM-KISAN: Farmer scheme - exclude only if explicitly False
    is_farmer = state.slots.get("is_landholding_farmer")
    if is_farmer is not False:  # None or True both allow consideration
        candidates.append("PM-KISAN")
    
    # PMMVY: Maternity scheme - only for females
    gender = state.slots.get("gender")
    if gender == "female":
        candidates.append("PMMVY")
    
    return candidates


def get_required_slots_for_schemes(
    target_schemes: Optional[List[str]] = None,
) -> List[str]:
    """
    Compute the set of slots required for the schemes the planner is considering.

    If no schemes are provided, we conservatively use all known schemes.
    """
    schemes = target_schemes or list(SCHEME_REQUIRED_SLOTS.keys())
    required: List[str] = []
    for scheme in schemes:
        for slot in SCHEME_REQUIRED_SLOTS.get(scheme, []):
            if slot not in required:
                required.append(slot)
    return required


def get_missing_slots(state: AgentState, required_slots: List[str]) -> List[str]:
    """Return list of required slots that are still None in memory."""
    missing = []
    for slot in required_slots:
        # Some required slots (e.g., age_at_childbirth) may not be part of the base SLOT_NAMES.
        value = state.slots.get(slot)
        if value is None:
            missing.append(slot)
    return missing


def choose_next_missing_slot(missing_slots: List[str]) -> Optional[str]:
    """Deterministic choice of which slot to ask for next."""
    return missing_slots[0] if missing_slots else None


def decide_next_action(
    state: AgentState,
    stt_confidence: float,
    target_schemes: Optional[List[str]] = None,
) -> Tuple[PlannerAction, Dict]:
    """
    Deterministic planner implementing the decision table.

    Returns:
      (action, info_dict)
      - info_dict may contain helper data like missing_slots, chosen_slot, etc.
    """
    info: Dict = {}

    # 1. STT confidence check
    if stt_confidence < 0.3:
        action = PlannerAction.REPEAT_INPUT
        state.last_action = action.value
        info["reason"] = "low_stt_confidence"
        return action, info

    # 2. Contradictions
    if state.contradictions:
        action = PlannerAction.HANDLE_CONTRADICTION
        state.last_action = action.value
        info["contradictions"] = list(state.contradictions)
        return action, info

    # 3. FIND_ELIGIBLE_SCHEME flow
    if state.intent == "FIND_ELIGIBLE_SCHEME":
        # Stage 1: Filter to candidate schemes based on known slots
        candidate_schemes = get_candidate_schemes(state)
        info["candidate_schemes"] = candidate_schemes
        
        # If no candidates yet, we may need more info to narrow down
        if not candidate_schemes:
            # Could ask for age or gender to narrow down, but for now
            # we'll use all schemes as fallback (conservative)
            candidate_schemes = list(SCHEME_REQUIRED_SLOTS.keys())
            info["candidate_schemes"] = candidate_schemes
            info["note"] = "no_candidates_yet_using_all"
        
        # Stage 2: Check if ANY candidate scheme has all required slots
        # If so, prioritize checking eligibility for that scheme
        complete_schemes = []
        for scheme in candidate_schemes:
            required_for_scheme = SCHEME_REQUIRED_SLOTS.get(scheme, [])
            missing_for_scheme = get_missing_slots(state, required_for_scheme)
            if not missing_for_scheme:
                complete_schemes.append(scheme)
        
        info["complete_schemes"] = complete_schemes
        
        # If we have at least one complete scheme, check eligibility
        if complete_schemes:
            if not state.eligibility_checked:
                action = PlannerAction.CHECK_ELIGIBILITY
            else:
                action = PlannerAction.RESPOND_RESULT
            state.last_action = action.value
            return action, info
        
        # Otherwise, check missing slots across all candidate schemes
        required = get_required_slots_for_schemes(candidate_schemes)
        missing = get_missing_slots(state, required)
        info["required_slots"] = required
        info["missing_slots"] = missing

        if missing:
            action = PlannerAction.ASK_MISSING_SLOT
            info["next_slot"] = choose_next_missing_slot(missing)
        elif not state.eligibility_checked:
            action = PlannerAction.CHECK_ELIGIBILITY
        else:
            action = PlannerAction.RESPOND_RESULT

        state.last_action = action.value
        return action, info

    # 4. APPLY_FOR_SCHEME flow
    if state.intent == "APPLY_FOR_SCHEME":
        if not state.eligibility_checked:
            action = PlannerAction.CHECK_ELIGIBILITY
        elif not state.documents or len(state.documents) == 0:
            # Documents not initialized yet
            action = PlannerAction.CHECK_DOCUMENTS
        else:
            # Check document readiness
            from app.services.documents import check_document_readiness
            
            doc_status = check_document_readiness(state.documents)
            
            if doc_status["status"] == "checking":
                # Still checking documents
                action = PlannerAction.CHECK_DOCUMENTS
                info["next_document"] = doc_status["next_doc"]
            elif doc_status["status"] == "missing":
                # Missing documents - explain
                action = PlannerAction.CHECK_DOCUMENTS  # Will be handled as "explain missing"
                info["missing_documents"] = doc_status["missing_docs"]
            elif doc_status["status"] == "ready":
                # All documents ready - confirm application
                if not state.application_started:
                    action = PlannerAction.CONFIRM_APPLICATION
                else:
                    action = PlannerAction.RESPOND_RESULT
            else:
                action = PlannerAction.CHECK_DOCUMENTS

        state.last_action = action.value
        return action, info

    # Fallback: treat as missing information
    action = PlannerAction.ASK_MISSING_SLOT
    state.last_action = action.value
    info["reason"] = "unhandled_intent_or_none"
    return action, info


def summarize_turn(
    state: AgentState,
    missing_slots: Optional[List[str]],
    action: PlannerAction,
    tool_called: Optional[str] = None,
    candidate_schemes: Optional[List[str]] = None,
) -> str:
    """
    Human-readable log line for debugging / demo:

    STATE:
    - Intent:
    - Candidate schemes:
    - Known slots:
    - Missing slots (for candidate):
    - Planner decision:
    - Tool called:
    """
    known_slots = {k: v for k, v in state.slots.items() if v is not None}
    summary_lines = [
        "STATE:",
        f"- Intent: {state.intent}",
    ]
    
    if candidate_schemes:
        summary_lines.append(f"- Candidate schemes: {candidate_schemes}")
    
    summary_lines.extend([
        f"- Known slots: {known_slots}",
        f"- Missing slots (for candidate): {missing_slots or []}",
        f"- Planner decision: {action.value}",
        f"- Tool called: {tool_called or 'None'}",
    ])
    return "\n".join(summary_lines)


