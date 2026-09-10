# VISTA

**Vernacular Intelligence for Smart Teaching and Adaptation**

VISTA is an offline-first classroom assistant for primary teachers who teach
in Hindi and support Santali-speaking learners. It helps a teacher explain a
lesson, provide the same content in Santali, check understanding, and respond
to learning gaps without depending on a continuous internet connection.

This project was prepared for **Smart India Hackathon 2026**.

- **Problem statement:** SIH26042
- **Theme:** Smart Education
- **Team ID:** T-07

## What it does

- Converts a teacher's Hindi text or speech into Santali text and audio.
- Provides approved lesson phrases and bundled audio when the network is
  unavailable.
- Checks learner responses and highlights class-level understanding gaps.
- Suggests re-teaching prompts, worksheets, and quick checks.
- Includes a bilingual classroom copilot for short, classroom-safe answers.
- Runs as a lightweight Android app using Capacitor, with a local FastAPI
  backend for development and model-backed features.

The main classroom path is:

**Teach -> Translate -> Check -> Understand -> Re-teach**

## Final presentation

The submission presentation is included here:

[SIH-2K26 VISTA Final Presentation](SIH-2K26-VISTA-Final.pptx)

## Project layout

```text
backend/                 FastAPI API and local model adapters
data/                    Seed curriculum and classroom data
frontend/                Capacitor Android classroom app
scripts/                 Model export and inference utilities
main.py                  Backend entry point
requirements.txt         Python dependencies
```

## Run the backend

Python 3.12 is recommended.

```powershell
python -m venv vista-env
.\vista-env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m backend.seed_database
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The default database is local SQLite. Cloud credentials are not required for
the bundled classroom flow. Local Ollama authoring is optional.

## Build the Android app

Install Node.js, Android Studio, and the Android SDK first.

```powershell
cd frontend
npm install
npm run build
npm run cap:sync
cd android
.\gradlew.bat --no-daemon assembleDebug
```

The debug APK is generated at:

```text
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

For an Android emulator using the development backend, the host computer is
available at `http://10.0.2.2:8000`. Start the backend with
`--host 0.0.0.0`.

## Offline use

The app bundles its classroom interface, seed content, reviewed lesson audio,
and offline phrase-bank fallbacks. Vosk and IndicTrans2 can be configured with
local model files using `.env.example`.

Arbitrary on-device translation still requires the selected local IndicTrans2
model to be downloaded and configured. The application is designed so that
approved classroom content remains usable when that model or the network is
not available.
