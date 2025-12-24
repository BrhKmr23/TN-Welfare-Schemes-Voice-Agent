# System Architecture

## Architecture Diagram (PlantUML)

```plantuml
@startuml TN_Welfare_Schemes_Voice_Agent_Architecture

!define RECTANGLE class

package "User Interface Layer" {
    [Streamlit UI\nstreamlit_app.py] as UI
    note right of UI
        - Voice input recording
        - Conversation display
        - Agent state visualization
        - Auto-processing pipeline
    end note
}

package "Application Core Layer" {
    [Agent State\nagent_state.py] as AgentState
    [Planner\nplanner.py] as Planner
    [Config\nconfig.py] as Config
    
    note right of AgentState
        - Intent tracking
        - Slot management
        - Document state
        - Contradiction detection
        - Application status
    end note
    
    note right of Planner
        - Decision table logic
        - Scheme pre-filtering
        - Action selection
        - Candidate scheme identification
    end note
}

package "Service Layer" {
    package "Audio Services" {
        [Audio Service\naudio.py] as Audio
        [STT Service\nstt.py] as STT
        [TTS Service\ntts.py] as TTS
    }
    
    package "NLU Services" {
        [Intent Service\nintent.py] as Intent
        [NLU Utils\nnlu_utils.py] as NLUUtils
        [Questions Service\nquestions.py] as Questions
    }
    
    package "Business Logic Services" {
        [Eligibility Service\neligibility.py] as Eligibility
        [Documents Service\ndocuments.py] as Documents
        [Application Service\napplication.py] as Application
    }
}

package "Data Layer" {
    [Schemes Data\nschemes.json] as Schemes
    note right of Schemes
        - Scheme definitions
        - Eligibility rules
        - Required documents
        - Scheme metadata
    end note
}

package "External Services" {
    [OpenAI Whisper\nSTT API] as Whisper
    [Google Gemini\nLLM API] as Gemini
    [Google TTS\ngTTS API] as gTTS
}

package "Utilities" {
    [API Key Checker\ncheck_api_key.py] as APIKeyCheck
}

' User Flow
UI --> Audio : Record voice
Audio --> STT : Audio file
STT --> Whisper : Transcribe Tamil speech
STT --> UI : Text + Confidence

UI --> Intent : User text
Intent --> Gemini : Extract intent & slots
Intent --> UI : NLU result

UI --> AgentState : Update state
AgentState --> Planner : Current state
Planner --> Config : Get config
Planner --> Schemes : Get scheme rules

Planner --> Eligibility : Check eligibility
Eligibility --> Schemes : Read rules
Eligibility --> Planner : Eligible schemes

Planner --> Documents : Check documents
Documents --> Schemes : Get required docs
Documents --> Planner : Document status

Planner --> Questions : Generate questions
Questions --> Gemini : Phrase contradictions
Questions --> UI : Tamil questions

Planner --> Application : Apply scheme
Application --> UI : Application result

UI --> TTS : Agent response
TTS --> gTTS : Generate speech
TTS --> UI : Audio file

' Service dependencies
Intent --> NLUUtils : Extract yes/no
Questions --> NLUUtils : Parse responses
Documents --> NLUUtils : Parse yes/no

' Configuration
Config --> Audio : Recording params
Config --> STT : Model config
Config --> TTS : Language config

' Utility
APIKeyCheck --> Gemini : Verify API key

@enduml
```

## Component Details

### 1. User Interface Layer
- **streamlit_app.py**: Main Streamlit application
  - Handles voice recording
  - Displays conversation history
  - Shows agent state in sidebar
  - Auto-processes recordings
  - Auto-plays responses

### 2. Application Core Layer

#### AgentState (agent_state.py)
- Manages conversation memory
- Tracks intent and slots
- Handles contradictions
- Stores document state
- Tracks application status

#### Planner (planner.py)
- Implements decision table
- Pre-filters candidate schemes
- Determines next action
- Manages conversation flow

#### Config (config.py)
- Centralized configuration
- Audio recording parameters
- Silence detection thresholds
- Language settings

### 3. Service Layer

#### Audio Services
- **audio.py**: Microphone recording, silence detection
- **stt.py**: Speech-to-text using Whisper
- **tts.py**: Text-to-speech using gTTS

#### NLU Services
- **intent.py**: Intent and slot extraction using Gemini
- **nlu_utils.py**: Yes/no extraction from Tamil
- **questions.py**: Tamil question generation

#### Business Logic Services
- **eligibility.py**: Deterministic eligibility checking
- **documents.py**: Document readiness tracking
- **application.py**: Mock application submission

### 4. Data Layer
- **schemes.json**: Scheme definitions, rules, required documents

### 5. External Services
- OpenAI Whisper (STT)
- Google Gemini (LLM)
- Google TTS (gTTS)

## Data Flow

```
User Voice Input
    ↓
[Audio Recording] → audio.py
    ↓
[STT] → stt.py → Whisper API
    ↓
[Text + Confidence]
    ↓
[NLU] → intent.py → Gemini API
    ↓
[Intent + Slots]
    ↓
[Update Memory] → agent_state.py
    ↓
[Planner Decision] → planner.py
    ↓
[Execute Action]
    ├─→ Eligibility Check → eligibility.py
    ├─→ Document Check → documents.py
    ├─→ Ask Question → questions.py
    └─→ Apply Scheme → application.py
    ↓
[Generate Response]
    ↓
[TTS] → tts.py → gTTS API
    ↓
[Audio Output] → Auto-play
```

## Key Design Patterns

1. **Service Layer Pattern**: Separation of concerns with dedicated service modules
2. **State Management**: Centralized agent state for conversation memory
3. **Deterministic Planning**: Rule-based planner without LLM decisions
4. **Context-Aware Processing**: Document/application responses bypass normal flow
5. **Modular Architecture**: Each component has a single responsibility

## File Organization

```
app/
├── __init__.py              # Package initialization
├── streamlit_app.py         # Main UI application
├── agent_state.py           # Conversation memory
├── planner.py               # Decision logic
├── config.py                # Configuration
├── schemes.json             # Scheme data
├── check_api_key.py         # API key verification
└── services/
    ├── __init__.py
    ├── audio.py             # Audio recording
    ├── stt.py               # Speech-to-text
    ├── tts.py               # Text-to-speech
    ├── intent.py            # Intent extraction
    ├── nlu_utils.py         # NLU utilities
    ├── questions.py         # Question generation
    ├── eligibility.py       # Eligibility engine
    ├── documents.py         # Document tracking
    └── application.py       # Application submission
```

