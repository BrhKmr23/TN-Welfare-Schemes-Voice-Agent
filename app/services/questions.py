"""Question generation for missing slots and contradiction handling.

This module uses LLM ONLY for Tamil phrasing, not for decision-making.
The planner decides what to ask; this module phrases it in Tamil.
"""

import os
from typing import Optional

try:
    from google import genai
except ImportError:
    genai = None  # Will use fallback questions if LLM not available


# Slot to question type mapping (locked)
SLOT_QUESTION_TYPES = {
    "age": "Ask exact number",
    "bpl_status": "Yes/No",
    "is_landholding_farmer": "Yes/No",
    "not_excluded_category": "Yes/No",
    "is_pregnant_or_lactating": "Yes/No",
    "meets_any_social_category": "Yes/No",
    "gender": "Male/Female",
}


def get_llm_client():
    """
    Get Gemini LLM client.
    
    Reads API key from GOOGLE_API_KEY environment variable.
    Set it from terminal:
        Windows: set GOOGLE_API_KEY=YOUR_KEY
        Linux/Mac: export GOOGLE_API_KEY=YOUR_KEY
    
    Returns:
        genai.Client if API key is available, None otherwise
    """
    if genai is None:
        return None  # Will trigger fallback in calling functions
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        # If client creation fails, return None to trigger fallback
        return None


CONTRADICTION_PROMPT = """You are a Tamil language assistant helping resolve contradictions in user information.

Task: Generate a polite Tamil message asking the user to clarify a contradiction.

Rules:
- Output ONLY the Tamil message text
- Do NOT add explanations
- Do NOT add English translations
- Keep it respectful and helpful
- Use respectful Tamil (நீங்கள் form)

Previous value: {previous_value}
New value: {new_value}
Slot name: {slot}

Generate the Tamil clarification request:"""


def ask_for_slot(slot: str) -> str:
    """
    Generate a Tamil question to ask for a specific slot.
    
    Args:
        slot: Slot name (e.g., "bpl_status", "age")
    
    Returns:
        Tamil question string
    
    Note:
        Uses default questions to avoid LLM calls (Gemini resource limits).
        The planner decides which slot to ask for.
    """
    # Use default questions directly (no LLM call)
    default_questions = {
        "age": "உங்கள் வயது என்ன?",
        "bpl_status": "நீங்கள் BPL / ஏழை பட்டியலில் உள்ளவரா?",
        "is_landholding_farmer": "நீங்கள் நிலம் வைத்திருக்கும் விவசாயியா?",
        "not_excluded_category": "நீங்கள் விலக்கப்பட்ட வகையில் இல்லையா?",
        "is_pregnant_or_lactating": "நீங்கள் கர்ப்பிணியா அல்லது தாய்ப்பால் கொடுப்பவரா?",
        "meets_any_social_category": "நீங்கள் சமூக பிரிவில் உள்ளவரா?",
        "gender": "உங்கள் பாலினம் என்ன?",
    }
    return default_questions.get(slot, f"தயவுசெய்து {slot} பற்றி தகவல் கொடுங்கள்.")


def handle_contradiction(slot: str, previous_value: any, new_value: any) -> str:
    """
    Generate a Tamil message to handle a contradiction.
    
    Args:
        slot: Slot name that has contradiction
        previous_value: Previously stored value
        new_value: New value that contradicts
    
    Returns:
        Tamil clarification request string
    
    Example:
        "முன்னர் நீங்கள் விவசாயி என்று சொன்னீர்கள், இப்போது இல்லை என்கிறீர்கள். எது சரி?"
    
    Note:
        Uses LLM for natural Tamil phrasing of contradiction messages.
    """
    # Convert values to readable Tamil
    def value_to_tamil(val):
        if val is True:
            return "ஆம்"
        elif val is False:
            return "இல்லை"
        elif isinstance(val, str):
            return val
        else:
            return str(val)
    
    prev_ta = value_to_tamil(previous_value)
    new_ta = value_to_tamil(new_value)
    
    prompt = CONTRADICTION_PROMPT.format(
        slot=slot,
        previous_value=prev_ta,
        new_value=new_ta
    )
    
    try:
        client = get_llm_client()
        if client is None:
            raise ImportError("LLM not available")
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt,
            config={"temperature": 0.3}
        )
        return response.text.strip()
    except Exception as e:
        # Fallback to simple Tamil contradiction message
        slot_names_ta = {
            "is_landholding_farmer": "விவசாயி",
            "bpl_status": "BPL பட்டியல்",
            "age": "வயது",
            "gender": "பாலினம்",
            "not_excluded_category": "விலக்கப்பட்ட வகை",
            "is_pregnant_or_lactating": "கர்ப்பிணி அல்லது தாய்ப்பால்",
            "meets_any_social_category": "சமூக பிரிவு",
        }
        slot_ta = slot_names_ta.get(slot, slot)
        return f"முன்னர் நீங்கள் {slot_ta} பற்றி '{prev_ta}' என்று சொன்னீர்கள், இப்போது '{new_ta}' என்கிறீர்கள். எது சரி?"


def ask_for_document(document: str) -> str:
    """
    Generate a Tamil question to ask if user has a specific document.
    
    Args:
        document: Document name (e.g., "aadhaar", "ration_card")
    
    Returns:
        Tamil question string
    
    Note:
        Uses default questions to avoid LLM calls (Gemini resource limits).
    """
    # Use default questions directly (no LLM call)
    default_questions = {
        "aadhaar": "உங்களிடம் ஆதார் இருக்கிறதா?",
        "ration_card": "உங்களிடம் ரேஷன் கார்டு இருக்கிறதா?",
        "bank_passbook": "உங்களிடம் வங்கி பாஸ்புக் இருக்கிறதா?",
        "age_proof": "உங்களிடம் வயது சான்றிதழ் இருக்கிறதா?",
        "land_document": "உங்களிடம் நிலம் சான்றிதழ் இருக்கிறதா?",
        "maternity_card": "உங்களிடம் மகப்பேறு கார்டு இருக்கிறதா?",
    }
    return default_questions.get(document, f"உங்களிடம் {document} இருக்கிறதா?")


def confirm_application(scheme_name_ta: str) -> str:
    """
    Generate a Tamil question to confirm if user wants to apply.
    
    Args:
        scheme_name_ta: Scheme name in Tamil
    
    Returns:
        Tamil confirmation question
    
    Note:
        Uses default message to avoid LLM calls (Gemini resource limits).
    """
    # Use default message directly (no LLM call)
    return f"இந்த திட்டத்திற்கு ({scheme_name_ta}) இப்போது விண்ணப்பிக்கலாமா?"


def explain_missing_document(document: str, scheme_name_ta: str) -> str:
    """
    Generate a Tamil message explaining that a document is required.
    
    Args:
        document: Document name
        scheme_name_ta: Scheme name in Tamil
    
    Returns:
        Tamil explanation message
    
    Note:
        Uses default messages to avoid LLM calls (Gemini resource limits).
    """
    # Use default messages directly (no LLM call)
    doc_names_ta = {
        "aadhaar": "ஆதார்",
        "ration_card": "ரேஷன் கார்டு",
        "bank_passbook": "வங்கி பாஸ்புக்",
        "age_proof": "வயது சான்றிதழ்",
        "land_document": "நிலம் சான்றிதழ்",
        "maternity_card": "மகப்பேறு கார்டு",
    }
    doc_ta = doc_names_ta.get(document, document)
    return f"இந்த திட்டத்திற்கு {doc_ta} அவசியம். அது கிடைத்த பிறகு விண்ணப்பிக்கலாம்."


def application_success_message(application_id: str) -> str:
    """
    Generate a Tamil success message after application submission.
    
    Args:
        application_id: Application ID
    
    Returns:
        Tamil success message
    
    Note:
        Uses default message to avoid LLM calls (Gemini resource limits).
    """
    # Use default message directly (no LLM call)
    return f"உங்கள் விண்ணப்பம் வெற்றிகரமாக பதிவு செய்யப்பட்டது. விண்ணப்ப எண்: {application_id}"

