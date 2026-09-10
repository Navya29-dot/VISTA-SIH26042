# VISTA — Vernacular Intelligence for Smart Teaching & Adaptation

**Smart India Hackathon 2026 · Problem Statement SIH26042**  
*AI-Powered Vernacular Pedagogy and Real-Time Translation Tool for Mother Tongue-Based Primary Education*

| | |
|---|---|
| **Theme** | Smart Education |
| **Category** | Software |
| **Team ID** | T-07 |
| **Team Name** | Mystic Wizard |

---

## The Problem

India's 2011 Census records 7.36 million Santali mother-tongue speakers, yet
ASER 2024 reports that 76.6% of Grade 3 rural government-school children
cannot read a Grade 2-level text — largely because their teacher does not
speak their language. Bilingual Hindi–Santali teachers are scarce, and most
translation tools stop at translation: they don't check whether a child
actually understood the lesson.

## What Makes VISTA Different

Unlike translation-only tools, **VISTA is built around one closed loop**:

```
TEACH → TRANSLATE → CHECK → UNDERSTAND → RE-TEACH
```

A teacher delivers a lesson in Hindi. VISTA translates it into Santali
(text + audio), checks whether the class understood, and if they didn't,
generates a different explanation instead of simply repeating the same
content. It closes the loop that translation-only apps leave open.

VISTA is designed to run on low-cost Android tablets with as little as 2GB of
RAM, without requiring an internet connection during class.

---

## Key Features

- **Live Translator** — Teacher speaks or types a line in Hindi; VISTA
  renders it in Santali text and audio, offline by default.
- **Understanding + Re-teach** — Detects learning gaps in real time through
  quick bilingual checks and generates a fresh explanation rather than a
  repeat.
- **AI Copilot** — Answers common teacher questions by matching them against
  a human-reviewed FAQ bank using local semantic search. It retrieves a
  pre-approved answer rather than generating unreviewed classroom content.
- **Practical classroom design** — Approved content, local storage, and
  bundled audio keep the core lesson flow available without the network.

---

## Architecture

### Content Authoring Layer

The authoring layer runs on a laptop or local server, not on the classroom
device:

```
FastAPI → Ollama (local LLM) + IndicTrans2 (self-hosted)
                         ↓
              Human / Native-Speaker Review
                         ↓
                  Approved Content Pack
```

Lesson drafts, worksheets, and translation drafts are generated locally.
Content is reviewed before it is packaged for classroom use.

### Classroom Runtime

```
Android App (Capacitor)
      │
      ├─ Local SQLite content and phrase bank
      ├─ IndicTrans2 local translation when configured
      ├─ Vosk local Hindi speech-to-text when configured
      └─ Pre-recorded lesson audio and Android device TTS
```

Retrieval comes first and model inference is used only when the required local
model is available. This keeps the classroom runtime suitable for constrained
devices.

---

## Offline / 2GB Design

The application bundles its classroom interface, seed content, reviewed
lesson audio, and offline phrase-bank fallbacks. Local Vosk and IndicTrans2
files can be configured for speech and translation.

The repository does not claim a final memory figure until it is measured on
the target emulator or device with:

```powershell
adb shell dumpsys meminfo org.vista.classroom
```

---

## Tech Stack

**Frontend / Classroom App**  
HTML5 · CSS3 · JavaScript · Capacitor · Android 9+

**Authoring Backend**  
Python · FastAPI · Uvicorn · SQLAlchemy · Pydantic · SQLite

**AI / NLP / Speech**  
Ollama (local authoring) · AI4Bharat IndicTrans2 · Vosk (offline speech
recognition)

**Offline Content Layer**  
SQLite · pre-recorded lesson audio · Santali/Ol Chiki content · worksheets
and flashcards

---

## Repository Structure

```text
vista/
├── backend/       FastAPI backend and local model adapters
├── data/          Seed curriculum and classroom data
├── frontend/      Capacitor Android classroom app
├── scripts/       Model export and inference utilities
├── ai.py          Local authoring and fallback logic
└── requirements.txt
```

## Getting Started

Python 3.12 is recommended.

```powershell
# Backend
python -m venv vista-env
.\vista-env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m backend.seed_database
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

To build the Android app:

```powershell
cd frontend
npm install
npm run build
npm run cap:sync
cd android
.\gradlew.bat --no-daemon assembleDebug
```

For an Android emulator using the development backend, use
`http://10.0.2.2:8000` and start the backend with `--host 0.0.0.0`.

## Known Limitations

- Final on-device RAM figures still require measurement with
  `adb shell dumpsys meminfo`.
- Santali pre-recorded audio is the primary speech-output path.
- Arbitrary local translation requires the IndicTrans2 model files to be
  downloaded and configured; approved classroom content remains available
  without them.
- Current validation has been performed on an Android emulator rather than a
  physical low-cost tablet.

## Research References

- Census of India, 2011 — Santali mother-tongue speaker population
- AI4Bharat, IndicTrans2 — open-source Hindi–Santali translation foundation
- NEP 2020 and NIPUN Bharat — mother-tongue instruction and foundational
  literacy policy
- ASER 2024 — rural reading-level data
