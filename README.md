# VISTA

VISTA means Vernacular Intelligence for Smart Teaching and Adaptation.

It is an AI-assisted classroom suite for Hindi-speaking primary teachers working with Santali, Ho, and Mundari-speaking learners. The prototype focuses on Santali and demonstrates offline-first lesson delivery, Hindi-to-Santali translation, bilingual worksheet generation, Understanding Pulse, and adaptive re-teaching.

For a judge-oriented setup and the honest offline/2GB validation status, see
[`JUDGE_GUIDE.md`](JUDGE_GUIDE.md).

## Project Structure

```text
Vista/
  backend/                 FastAPI backend
  data/                    Seed curriculum data
  frontend/                Capacitor Android classroom app
  main.py                  Starts backend and frontend together
  requirements.txt         Python dependencies
  TECHNOLOGY_FLOW.md       Technologies and architecture flow
  METHODOLOGY_AND_WORKFLOW.md
```

## Run Backend

```powershell
cd C:\Users\navya\Downloads\Vista\Vista
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The default backend uses a local SQLite database and never contacts a cloud API.
For authoring, install Ollama while online, pull the configured model, then run
`ollama serve`; after that the authoring API uses only `127.0.0.1`.

## Prepare the offline translation model

Do not guess the AI4Bharat checkpoint name. Confirm the distilled indic-indic
checkpoint and its parameter count first, then export and quantize it:

```powershell
python -m pip install -r requirements.txt
python scripts\export_indictrans2_onnx.py --model-id <confirmed-local-or-HF-checkpoint> --output D:\AIModels\indictrans2-int8
```

Set `INDICTRANS2_MODEL_NAME` to the exported local model directory and keep
`INDICTRANS2_LOCAL_FILES_ONLY=true`. Run one desktop inference before testing
the same model with Vosk and the phrase bank loaded on a 2048 MB Android
emulator. Record the actual `adb shell dumpsys meminfo` TOTAL PSS; do not use
an estimate in the presentation.

## Run Android App

```powershell
cd C:\Users\navya\Downloads\Vista\Vista\frontend
npm install
npm run cap:prepare
npm run cap:sync
cd android
.\gradlew.bat --no-daemon assembleDebug
.\gradlew.bat installDebug
```

If Gradle fails with `Unsupported class file major version 69`, it is using Java 25. This project pins Android Studio JBR in `frontend/android/gradle.properties`.

If Gradle fails with `The paging file is too small`, close heavy apps or increase Windows virtual memory before rebuilding.

## Prototype Highlights

- Local IndicTrans2 endpoint for arbitrary Hindi-to-Santali text translation.
- Offline voice bridge path using Vosk Hindi ASR plus IndicTrans2.
- Approved phrase pack fallback for low-connectivity classrooms.
- Included lesson audio: `Science.wav`, `Science santali.wav`, and `hindi santali.wav`.
- Dynamic Understanding Pulse with learner evidence and misconception tracking.
- Re-teach plan synced to the current class misconception.
- Performance-based personalized worksheets: weak concepts and accuracy determine focus and difficulty;
  local Ollama authoring is optional, while the measured-gap template remains available offline.
- Floating bilingual Hindi/Santali AI Copilot backed by `/copilot`.
- Lesson co-pilot icon that suggests quick checks and re-teach cues.
- Hindi speech → local Vosk transcription → local IndicTrans2 Hindi-to-Santali translation is offline
  when the models are installed. Speech output uses bundled reviewed recordings or the Android device voice.
