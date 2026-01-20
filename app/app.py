"""Complete Tamil Voice Agent Demo - Streamlit App.

This app demonstrates the full agentic workflow:
STT → NLU → Memory → Planner → Tools → TTS
"""

import os
import sys
import json
from typing import Dict, Any

import streamlit as st

# Ensure project root is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.agent_state import AgentState, update_state_from_nlu
from app.planner import decide_next_action, PlannerAction, summarize_turn
from app.services import audio, stt, tts, intent
from app.services.eligibility import check_eligibility
from app.services.documents import (
    initialize_document_state,
    check_document_readiness,
    get_required_documents,
)
from app.services.application import apply_for_scheme
from app.services.questions import (
    ask_for_slot,
    handle_contradiction,
    ask_for_document,
    confirm_application,
    explain_missing_document,
    application_success_message,
)
from app.services.nlu_utils import extract_yes_no_from_tamil


# Page config
st.set_page_config(
    page_title="Tamil Voice Agent - Demo",
    page_icon="🎙️",
    layout="wide",
)

# Initialize session state
if "agent_state" not in st.session_state:
    st.session_state.agent_state = AgentState()

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "current_audio_path" not in st.session_state:
    st.session_state.current_audio_path = None

if "last_response_audio" not in st.session_state:
    st.session_state.last_response_audio = None

if "auto_process_pending" not in st.session_state:
    st.session_state.auto_process_pending = False

if "pending_audio_path" not in st.session_state:
    st.session_state.pending_audio_path = None


def format_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
    """Format slots for display (remove None values)."""
    return {k: v for k, v in slots.items() if v is not None}


def get_scheme_name_ta(scheme_id: str) -> str:
    """Get Tamil name for a scheme."""
    scheme_names = {
        "CEN_IGNOAPS_001": "இந்திரா காந்தி தேசிய முதியோர் ஓய்வூதிய திட்டம்",
        "CEN_PM_KISAN_001": "பிரதமர் கிசான் சம்மான் நிதி",
        "CEN_PMMVY_001": "பிரதமர் மாத்ரு வந்தனா யோஜனா",
    }
    return scheme_names.get(scheme_id, scheme_id)


def process_user_input(audio_path: str) -> Dict[str, Any]:
    """Process user voice input through full agent pipeline."""
    result = {
        "user_text": "",
        "nlu_result": {},
        "planner_action": None,
        "agent_response": "",
        "response_audio": None,
        "tool_called": None,
        "error": None,
        "debug_steps": [],  # Add debug steps
    }

    try:
        # Step 1: STT
        result["debug_steps"].append("🔊 Step 1: STT (Speech-to-Text)")
        user_text, stt_confidence = stt.speech_to_text(audio_path)
        result["user_text"] = user_text
        result["debug_steps"].append(f"   ✓ Recognized: '{user_text}'")
        result["debug_steps"].append(f"   ✓ STT Confidence: {stt_confidence:.2f}")

        if len(user_text.strip()) < 3:
            result["error"] = "Speech not clear. Please try again."
            result["debug_steps"].append(f"   ✗ Error: Text too short")
            return result

        # Step 2: NLU (Intent + Slots)
        result["debug_steps"].append("🧠 Step 2: NLU (Intent + Slot Extraction)")
        nlu_result = intent.extract_intent_and_slots(user_text)
        result["nlu_result"] = nlu_result
        result["debug_steps"].append(f"   ✓ Intent: {nlu_result.get('intent')}")
        result["debug_steps"].append(f"   ✓ Slots: {json.dumps({k: v for k, v in nlu_result.get('slots', {}).items() if v is not None}, ensure_ascii=False)}")

        # Step 3: Update Memory
        result["debug_steps"].append("💾 Step 3: Update Memory")
        state = st.session_state.agent_state
        update_state_from_nlu(state, nlu_result)
        result["debug_steps"].append(f"   ✓ State updated: Intent={state.intent}, Slots filled={len([k for k, v in state.slots.items() if v is not None])}")

        # Step 4: Check for document/application responses FIRST (bypass STT confidence check)
        result["debug_steps"].append("🎯 Step 4: Check Context (Document/Application)")
        agent_response = ""
        tool_called = None
        handled_by_context = False
        context_action = None

        # Check if we're waiting for a document response (last action was CHECK_DOCUMENTS)
        if state.last_action == PlannerAction.CHECK_DOCUMENTS.value and state.documents:
            doc_status = check_document_readiness(state.documents)
            if doc_status["status"] == "checking":
                next_doc = doc_status["next_doc"]
                # Extract yes/no from user speech (even with low STT confidence)
                yes_no = extract_yes_no_from_tamil(user_text)
                if yes_no:
                    result["debug_steps"].append(f"   ✓ Document response detected: {yes_no} for {next_doc} (bypassed STT confidence check)")
                    state.documents[next_doc] = yes_no
                    # Re-check document status after update
                    doc_status = check_document_readiness(state.documents)
                    if doc_status["status"] == "checking":
                        # Ask next document
                        next_doc = doc_status["next_doc"]
                        agent_response = ask_for_document(next_doc)
                        tool_called = f"ask_for_document({next_doc})"
                        state.last_action = PlannerAction.CHECK_DOCUMENTS.value
                        context_action = PlannerAction.CHECK_DOCUMENTS
                        handled_by_context = True
                    elif doc_status["status"] == "missing":
                        missing_docs = doc_status["missing_docs"]
                        if missing_docs and state.eligible_schemes:
                            scheme_id = state.eligible_schemes[0]
                            scheme_name_ta = get_scheme_name_ta(scheme_id)
                            agent_response = explain_missing_document(missing_docs[0], scheme_name_ta)
                            tool_called = f"explain_missing_document({missing_docs[0]})"
                            handled_by_context = True
                    elif doc_status["status"] == "ready":
                        # All documents ready, confirm application
                        if state.eligible_schemes:
                            scheme_id = state.eligible_schemes[0]
                            scheme_name_ta = get_scheme_name_ta(scheme_id)
                            agent_response = confirm_application(scheme_name_ta)
                            tool_called = "confirm_application"
                            state.last_action = PlannerAction.CONFIRM_APPLICATION.value
                            context_action = PlannerAction.CONFIRM_APPLICATION
                            handled_by_context = True
                else:
                    # Didn't understand yes/no, ask again (but don't fail due to low STT confidence)
                    agent_response = ask_for_document(next_doc)
                    tool_called = f"ask_for_document({next_doc})"
                    result["debug_steps"].append(f"   → Could not extract yes/no, re-asking (bypassed STT confidence)")
                    handled_by_context = True
        
        # Check if waiting for application confirmation (last action was CONFIRM_APPLICATION)
        if not handled_by_context and state.last_action == PlannerAction.CONFIRM_APPLICATION.value and not state.application_started:
            # User might be confirming application
            yes_no = extract_yes_no_from_tamil(user_text)
            if yes_no == "yes":
                # Apply for scheme
                scheme_id = state.eligible_schemes[0]
                result = apply_for_scheme(scheme_id, state.slots)
                state.application_started = True
                state.application_id = result["application_id"]
                agent_response = application_success_message(result["application_id"])
                tool_called = f"apply_for_scheme({scheme_id})"
                state.last_action = PlannerAction.APPLY_SCHEME.value
                context_action = PlannerAction.APPLY_SCHEME
                handled_by_context = True
            elif yes_no == "no":
                agent_response = "விண்ணப்பம் ரத்து செய்யப்பட்டது. நன்றி!"
                tool_called = "cancel_application"
                handled_by_context = True
            else:
                # Re-ask confirmation
                scheme_id = state.eligible_schemes[0]
                scheme_name_ta = get_scheme_name_ta(scheme_id)
                agent_response = confirm_application(scheme_name_ta)
                tool_called = "confirm_application"
                result["debug_steps"].append(f"   → Could not extract yes/no for application confirmation, re-asking")
                handled_by_context = True

        # Set planner_action for context-handled cases
        if handled_by_context and context_action:
            result["planner_action"] = context_action
            result["planner_info"] = {"handled_by_context": True}

        # Step 5: Planner Decision (only if not handled by context)
        if not handled_by_context:
            result["debug_steps"].append("🎯 Step 5: Planner Decision")
            # Use actual STT confidence, not NLU confidence
            action, info = decide_next_action(state, stt_confidence)
            result["planner_action"] = action
            result["planner_info"] = info
            result["debug_steps"].append(f"   ✓ Action: {action.value}")
            result["debug_steps"].append(f"   ✓ Info: {json.dumps(info, ensure_ascii=False, default=str)}")

            # Step 6: Execute Action
            result["debug_steps"].append("⚙️ Step 6: Execute Action")
            
            if action == PlannerAction.REPEAT_INPUT:
                result["debug_steps"].append("   → Action: REPEAT_INPUT")
                agent_response = "மன்னிக்கவும், தெளிவாக கேட்க முடியவில்லை. தயவுசெய்து மீண்டும் சொல்லுங்கள்."

            elif action == PlannerAction.HANDLE_CONTRADICTION:
                contradictions = info.get("contradictions", [])
                if contradictions:
                    slot = contradictions[0]
                    prev_val = state.slots.get(slot)
                    # Get new value from NLU
                    new_val = nlu_result.get("slots", {}).get(slot)
                    agent_response = handle_contradiction(slot, prev_val, new_val)
                    tool_called = "handle_contradiction"

            elif action == PlannerAction.ASK_MISSING_SLOT:
                slot = info.get("next_slot")
                if slot:
                    agent_response = ask_for_slot(slot)
                    tool_called = f"ask_for_slot({slot})"

            elif action == PlannerAction.CHECK_ELIGIBILITY:
                result["debug_steps"].append("   → Action: CHECK_ELIGIBILITY")
                eligible_schemes = check_eligibility(state.slots)
                result["debug_steps"].append(f"   ✓ Eligible schemes found: {len(eligible_schemes)}")
                state.eligibility_checked = True
                state.eligible_schemes = [s["scheme_id"] for s in eligible_schemes]

                if eligible_schemes:
                    scheme_names = [get_scheme_name_ta(s["scheme_id"]) for s in eligible_schemes]
                    reasons = [s["reason_ta"] for s in eligible_schemes]
                    agent_response = f"நீங்கள் தகுதியான திட்டங்கள்:\n"
                    for name, reason in zip(scheme_names, reasons):
                        agent_response += f"• {name}: {reason}\n"
                else:
                    agent_response = "துரதிர்ஷ்டவசமாக, நீங்கள் தற்போது எந்த திட்டத்திற்கும் தகுதியானவர் அல்ல."

                tool_called = "check_eligibility"

            elif action == PlannerAction.CHECK_DOCUMENTS:
                # Initialize documents if needed
                if not state.documents and state.eligible_schemes:
                    scheme_id = state.eligible_schemes[0]
                    state.documents = initialize_document_state(scheme_id)

                doc_status = check_document_readiness(state.documents)

                if doc_status["status"] == "checking":
                    next_doc = doc_status["next_doc"]
                    agent_response = ask_for_document(next_doc)
                    tool_called = f"ask_for_document({next_doc})"
                    state.last_action = PlannerAction.CHECK_DOCUMENTS.value

                elif doc_status["status"] == "missing":
                    missing_docs = doc_status["missing_docs"]
                    if missing_docs and state.eligible_schemes:
                        scheme_id = state.eligible_schemes[0]
                        scheme_name_ta = get_scheme_name_ta(scheme_id)
                        agent_response = explain_missing_document(missing_docs[0], scheme_name_ta)
                        tool_called = f"explain_missing_document({missing_docs[0]})"

            elif action == PlannerAction.CONFIRM_APPLICATION:
                if state.eligible_schemes:
                    scheme_id = state.eligible_schemes[0]
                    scheme_name_ta = get_scheme_name_ta(scheme_id)
                    agent_response = confirm_application(scheme_name_ta)
                    tool_called = "confirm_application"
                    state.last_action = PlannerAction.CONFIRM_APPLICATION.value

            elif action == PlannerAction.APPLY_SCHEME:
                if state.eligible_schemes:
                    scheme_id = state.eligible_schemes[0]
                    result = apply_for_scheme(scheme_id, state.slots)
                    state.application_started = True
                    state.application_id = result["application_id"]
                    agent_response = application_success_message(result["application_id"])
                    tool_called = f"apply_for_scheme({scheme_id})"
                    state.last_action = PlannerAction.APPLY_SCHEME.value

            elif action == PlannerAction.RESPOND_RESULT:
                if state.eligible_schemes:
                    scheme_names = [get_scheme_name_ta(sid) for sid in state.eligible_schemes]
                    agent_response = f"நீங்கள் தகுதியான திட்டங்கள்: {', '.join(scheme_names)}"
                else:
                    agent_response = "மேலும் தகவல் தேவை."

        result["agent_response"] = agent_response
        result["tool_called"] = tool_called
        result["debug_steps"].append(f"   ✓ Response generated: {len(agent_response)} chars")

        # Step 6: TTS
        if agent_response:
            result["debug_steps"].append("🔊 Step 6: TTS (Text-to-Speech)")
            response_audio = tts.text_to_speech(agent_response)
            result["response_audio"] = response_audio
            result["debug_steps"].append("   ✓ Audio generated")

    except Exception as e:
        result["error"] = str(e)
        result["debug_steps"].append(f"   ✗ ERROR: {str(e)}")
        import traceback
        result["traceback"] = traceback.format_exc()

    return result


# UI Layout
st.title("🎙️ Tamil Voice Agent - Complete Demo")
st.markdown("**Agentic AI System for Government Welfare Scheme Assistance**")

# Sidebar - State Display
with st.sidebar:
    st.header("📊 Agent State")
    
    state = st.session_state.agent_state
    
    st.subheader("Intent")
    st.write(state.intent or "None")
    
    st.subheader("Known Slots")
    known_slots = format_slots(state.slots)
    if known_slots:
        st.json(known_slots)
    else:
        st.write("_No slots filled yet_")
    
    st.subheader("Eligible Schemes")
    if state.eligible_schemes:
        for sid in state.eligible_schemes:
            st.write(f"• {get_scheme_name_ta(sid)}")
    else:
        st.write("_Not checked yet_")
    
    st.subheader("Documents")
    if state.documents:
        st.json(state.documents)
    else:
        st.write("_Not initialized_")
    
    st.subheader("Application")
    if state.application_id:
        st.success(f"✅ Submitted: {state.application_id}")
    elif state.application_started:
        st.info("⏳ In progress...")
    else:
        st.write("_Not started_")
    
    st.subheader("Contradictions")
    if state.contradictions:
        st.warning(f"⚠️ {state.contradictions}")
    else:
        st.write("_None_")
    
    # Reset button
    if st.button("🔄 Reset Session", type="secondary"):
        st.session_state.agent_state = AgentState()
        st.session_state.conversation_history = []
        st.session_state.current_audio_path = None
        st.session_state.last_response_audio = None
        st.rerun()

# Main area - Conversation
col1, col2 = st.columns([2, 1])

with col1:
    st.header("💬 Conversation")
    
    # Display conversation history
    for i, turn in enumerate(st.session_state.conversation_history):
        with st.expander(f"Turn {i+1}: {turn.get('planner_action', 'N/A')}", expanded=(i == len(st.session_state.conversation_history) - 1)):
            st.markdown("**User:**")
            st.write(turn.get("user_text", ""))
            
            st.markdown("**Agent:**")
            st.write(turn.get("agent_response", ""))
            
            if turn.get("response_audio"):
                st.audio(turn["response_audio"])
            
            # Debug information
            if turn.get("debug_steps"):
                with st.expander("🔍 Debug Steps", expanded=False):
                    for step in turn["debug_steps"]:
                        st.text(step)
            
            st.markdown("**NLU Result:**")
            nlu = turn.get("nlu_result", {})
            st.json({
                "intent": nlu.get("intent"),
                "slots": {k: v for k, v in nlu.get("slots", {}).items() if v is not None},
                "confidence": nlu.get("confidence"),
            })
            
            st.markdown("**Planner Decision:**")
            st.code(turn.get("planner_action", ""))
            
            if turn.get("planner_info"):
                st.markdown("**Planner Info:**")
                st.json(turn["planner_info"])
            
            if turn.get("tool_called"):
                st.markdown("**Tool Called:**")
                st.code(turn["tool_called"])

with col2:
    st.header("🎤 Voice Input")
    
    # Auto-process if we have pending audio
    if st.session_state.auto_process_pending and st.session_state.pending_audio_path:
        with st.spinner("Processing..."):
            result = process_user_input(st.session_state.pending_audio_path)
            
            if result["error"]:
                st.error(f"❌ Error: {result['error']}")
                if result.get("debug_steps"):
                    st.markdown("**Debug Steps:**")
                    for step in result["debug_steps"]:
                        st.text(step)
                if "traceback" in result:
                    with st.expander("🔍 Full Traceback"):
                        st.code(result["traceback"])
                st.session_state.auto_process_pending = False
                st.session_state.pending_audio_path = None
            else:
                # Add to conversation history
                turn = {
                    "user_text": result["user_text"],
                    "nlu_result": result["nlu_result"],
                    "planner_action": result["planner_action"].value if result["planner_action"] else None,
                    "agent_response": result["agent_response"],
                    "response_audio": result["response_audio"],
                    "tool_called": result["tool_called"],
                    "debug_steps": result.get("debug_steps", []),
                    "planner_info": result.get("planner_info", {}),
                }
                st.session_state.conversation_history.append(turn)
                st.session_state.last_response_audio = result["response_audio"]
                st.session_state.auto_process_pending = False
                st.session_state.pending_audio_path = None
                st.rerun()
    
    if st.button("🎙️ Start Recording", type="primary", use_container_width=True):
        with st.spinner("Recording... Speak now"):
            audio_path = audio.record_until_silence()
            if audio_path:
                st.session_state.pending_audio_path = audio_path
                st.session_state.auto_process_pending = True
                st.success("✅ Recording complete! Processing automatically...")
                st.rerun()
            else:
                st.error("❌ Recording failed")
    
    # Auto-play last response audio
    if st.session_state.last_response_audio:
        st.audio(st.session_state.last_response_audio, autoplay=True)
        # Clear after playing (prevent re-playing on rerun)
        if not st.session_state.auto_process_pending:
            st.session_state.last_response_audio = None

# Document status display (informational only - voice-based interaction)
if st.session_state.agent_state.documents:
    doc_status = check_document_readiness(st.session_state.agent_state.documents)
    if doc_status["status"] == "checking":
        next_doc = doc_status["next_doc"]
        st.info(f"💬 Waiting for voice response about: {next_doc}")
        st.caption("Say 'ஆம்' (yes) or 'இல்லை' (no) when asked")

# Footer
st.markdown("---")
st.caption("**Demo Mode** - All steps are transparent and logged for evaluation")

