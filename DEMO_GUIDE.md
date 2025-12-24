# Demo Guide - Tamil Voice Agent

## Quick Start

1. **Activate virtual environment:**
```bash
voiceagent\Scripts\activate  # Windows
```

2. **Set API key:**
```bash
set GOOGLE_API_KEY=YOUR_KEY
```

3. **Run the demo:**
```bash
streamlit run app/streamlit_app.py
```

## Demo Flow

### Main Interface

**Left Panel (Main):**
- Conversation history with all turns
- Each turn shows:
  - User input (Tamil text)
  - Agent response (Tamil text + audio)
  - Planner decision
  - Tool called

**Right Panel:**
- Voice recording button
- Process recording button
- Current audio playback

**Sidebar:**
- Real-time agent state display
- Intent, slots, eligible schemes
- Document status
- Application status
- Reset button

### Demo Scenarios

#### Scenario 1: Basic Eligibility Finding
1. Click "Start Recording"
2. Say: "நான் 65 வயது, BPL பட்டியலில் உள்ளேன்"
3. Click "Process Recording"
4. Watch: Planner → CHECK_ELIGIBILITY → Shows eligible schemes

#### Scenario 2: Missing Information
1. Say: "நான் விவசாயி"
2. Watch: Planner → ASK_MISSING_SLOT → Agent asks for more info
3. Say: "ஆம், விலக்கப்பட்ட வகையில் இல்லை"
4. Watch: Eligibility checked → Shows PM-KISAN eligible

#### Scenario 3: Contradiction Handling
1. Say: "நான் விவசாயி"
2. Say: "நான் IT வேலை செய்கிறேன், விவசாயி இல்லை"
3. Watch: Planner → HANDLE_CONTRADICTION → Agent asks for clarification
4. Say: "மன்னிக்கவும், நான் விவசாயி இல்லை"
5. Watch: Contradiction cleared → Flow continues

#### Scenario 4: Document Checking
1. Complete eligibility check (Scenario 1)
2. Change intent to APPLY_FOR_SCHEME
3. Watch: Planner → CHECK_DOCUMENTS
4. Use document buttons (Yes/No/Skip) to update status
5. Watch: If missing → Explains requirement

#### Scenario 5: Complete Application
1. Complete eligibility + all documents marked "yes"
2. Watch: Planner → CONFIRM_APPLICATION
3. Click "Confirm Application"
4. Watch: Application submitted → Success message with ID

## Key Features to Highlight

✅ **Transparent Planning** - Every decision is logged and visible  
✅ **Smart Questioning** - Only asks relevant questions (no pregnancy to men)  
✅ **Memory Persistence** - Remembers context across turns  
✅ **Contradiction Resolution** - Handles user corrections gracefully  
✅ **Document Management** - Checks all required documents  
✅ **End-to-End Flow** - From eligibility to application submission  

## Test Cases

Run test cases to see automated scenarios:

```bash
python -m app.sample_test_cases
```

**5 Test Cases:**
1. Basic eligibility finding
2. Missing slots flow
3. Contradiction resolution
4. Document checking (missing doc)
5. Complete application flow

## Troubleshooting

**Audio not recording:**
- Check microphone permissions
- Try different audio device
- Check silence threshold in config

**LLM errors:**
- Verify GOOGLE_API_KEY is set
- Check internet connection
- Fallback questions will be used if LLM unavailable

**Import errors:**
- Make sure you're in project root directory
- Activate virtual environment
- Run: `pip install -r requirements.txt`

