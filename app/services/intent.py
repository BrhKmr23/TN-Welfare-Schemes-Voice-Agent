import json
import os
import re
from typing import Callable, Dict, Optional

from google import genai

INTENT_SLOT_PROMPT = """
You are an information extraction system.

Task:
Given a Tamil user utterance, extract:
1. intent
2. slots
3. confidence

STRICT RULES:
- Output ONLY valid JSON
- Do NOT add explanations
- Do NOT translate the text
- Do NOT infer missing information
- If a slot is not explicitly mentioned, keep it null
- Do NOT decide eligibility
- Do NOT ask questions

INTENT RULES:
- Default intent: FIND_ELIGIBLE_SCHEME
- If the user says “விண்ணப்பிக்க” → APPLY_FOR_SCHEME
- If the user asks “இந்த திட்டம் என்ன”, “விவரம்” → GET_SCHEME_DETAILS

SLOTS (use exactly these keys):
age (integer or null)
bpl_status (true/false/null)
is_landholding_farmer (true/false/null)
not_excluded_category (true/false/null)
is_pregnant_or_lactating (true/false/null)
meets_any_social_category (true/false/null)
gender ("male" | "female" | null)

Return JSON in this exact shape:

{{
  "intent": "...",
  "slots": {{
    "age": null,
    "bpl_status": null,
    "is_landholding_farmer": null,
    "not_excluded_category": null,
    "is_pregnant_or_lactating": null,
    "meets_any_social_category": null,
    "gender": null
  }},
  "confidence": 0.0
}}

Tamil input:
\"\"\"{text}\"\"\"
"""


def extract_json_from_text(text: str) -> str:
    """Extract JSON from text that might be wrapped in markdown code blocks."""
    text = re.sub(r"```json\s*\n?", "", text)
    text = re.sub(r"```\s*\n?", "", text)
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return text.strip()


def _build_llm(api_key: Optional[str] = None, model_name: str = "models/gemini-2.5-flash"):
    """
    Build Gemini LLM client.
    
    Reads API key from GOOGLE_API_KEY environment variable if not provided.
    Set it from terminal:
        Windows: set GOOGLE_API_KEY=YOUR_KEY
        Linux/Mac: export GOOGLE_API_KEY=YOUR_KEY
    """
    key = api_key or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set. "
            "Set it from terminal:\n"
            "  Windows: set GOOGLE_API_KEY=YOUR_KEY\n"
            "  Linux/Mac: export GOOGLE_API_KEY=YOUR_KEY"
        )
    try:
        client = genai.Client(api_key=key)
        return client, model_name
    except Exception as e:
        raise ValueError(f"Failed to create Gemini client: {e}. Check your API key.")


def create_llm_call_fn(api_key: Optional[str] = None, model_name: str = "models/gemini-2.5-flash") -> Callable[[str, float], str]:
    """Factory returning a thin wrapper around google.genai generate_content."""
    client, model = _build_llm(api_key=api_key, model_name=model_name)

    def llm_call_fn(prompt: str, temperature: float = 0.0) -> str:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"temperature": temperature},
        )
        return response.text

    return llm_call_fn


def extract_intent_and_slots(text: str, llm_call_fn: Optional[Callable[[str, float], str]] = None) -> Dict:
    """Extract intent JSON using the provided llm_call_fn (or default Gemini)."""
    if llm_call_fn is None:
        llm_call_fn = create_llm_call_fn()

    prompt = INTENT_SLOT_PROMPT.format(text=text)
    raw_output = llm_call_fn(prompt=prompt, temperature=0.0)

    try:
        json_text = extract_json_from_text(raw_output)
        parsed = json.loads(json_text)
    except (json.JSONDecodeError, AttributeError):
        parsed = {
            "intent": "FIND_ELIGIBLE_SCHEME",
            "slots": {
                "age": None,
                "bpl_status": None,
                "is_landholding_farmer": None,
                "not_excluded_category": None,
                "is_pregnant_or_lactating": None,
                "meets_any_social_category": None,
                "gender": None,
            },
            "confidence": 0.5,
        }

    return parsed

