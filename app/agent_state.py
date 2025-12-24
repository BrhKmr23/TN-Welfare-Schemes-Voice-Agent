from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SLOT_NAMES = [
    "age",
    "bpl_status",
    "is_landholding_farmer",
    "not_excluded_category",
    "is_pregnant_or_lactating",
    "meets_any_social_category",
    "gender",
]


@dataclass
class AgentState:
    """
    Deterministic agent memory.

    NOTE: Field names and structure are frozen to match the assignment spec.
    """

    intent: Optional[str] = None
    slots: Dict[str, Any] = field(
        default_factory=lambda: {name: None for name in SLOT_NAMES}
    )

    confirmed_slots: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)

    eligibility_checked: bool = False
    eligible_schemes: List[str] = field(default_factory=list)

    documents: Dict[str, Any] = field(default_factory=dict)
    application_started: bool = False
    application_id: Optional[str] = None

    last_action: Optional[str] = None


def update_state_from_nlu(state: AgentState, nlu_result: Dict[str, Any]) -> None:
    """
    Mechanical memory update after each user utterance.

    nlu_result is expected to have:
      - "intent": str
      - "slots": {slot_name: value}
    """
    intent = nlu_result.get("intent")
    slots = nlu_result.get("slots", {}) or {}

    # (a) Update intent only if not set or explicitly changed
    if intent and (state.intent is None or state.intent != intent):
        state.intent = intent

    # (b) Update slots + contradictions
    for slot_name, new_value in slots.items():
        if slot_name not in state.slots:
            continue

        if new_value is None:
            # Do not overwrite an existing value with null
            continue

        current_value = state.slots[slot_name]

        if current_value is not None and current_value != new_value:
            # Contradiction
            state.contradictions.append(slot_name)
        else:
            # First time we see this slot or same value again
            state.slots[slot_name] = new_value
            state.confirmed_slots.append(slot_name)


