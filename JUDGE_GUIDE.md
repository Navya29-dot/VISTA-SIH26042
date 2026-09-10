# VISTA SIH26042 — Judge Evaluation Guide

VISTA is an offline-first classroom system for Hindi-speaking teachers and
Santali-speaking learners. The repository contains the FastAPI backend, local
SQLite curriculum data, Capacitor Android application, reviewed lesson audio,
and the scripts needed to prepare the local translation model.

## Quick demo

### Backend

Use Python 3.12 on Windows. Keep the repository and temporary package files on
a drive with free space.

```powershell
python -m venv vista-env
.\vista-env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m backend.seed_database
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Check `http://127.0.0.1:8000/`. The API uses SQLite and does not require
PostgreSQL, Groq, Sarvam, or cloud credentials.

### Android app

Install Node.js, Android Studio, and an Android SDK. Then:

```powershell
cd frontend
npm install
npm run build
npm run cap:sync
cd android
.\gradlew.bat --no-daemon assembleDebug
```

Install `app\build\outputs\apk\debug\app-debug.apk` on an emulator or device.
The app includes lesson UI and reviewed Hindi/Santali audio in its assets.

For an emulator calling the development backend, the Android host address is
`http://10.0.2.2:8000`; start the API with `--host 0.0.0.0`.

## Offline verification

1. Launch the app and test lesson navigation and bundled audio.
2. Enable airplane mode on the emulator.
3. Force-stop and relaunch the app.
4. Confirm bundled lessons, audio, local database-backed screens, and
   deterministic fallback responses still work.
5. For local speech/translation, configure downloaded Vosk and IndicTrans2
   files using `.env.example`.

The current Android package is offline-first. Fully on-device arbitrary
translation requires bundling the confirmed distilled IndicTrans2 INT8 ONNX
model and connecting it through a native ONNX Runtime Capacitor plugin. The
repository includes the ONNX export/quantization preparation script and does
not guess an AI4Bharat checkpoint name.

## 2 GB measurement

Create an emulator with RAM set to exactly 2048 MB. After exercising the app:

```powershell
adb shell dumpsys meminfo org.vista.classroom
```

Record the `TOTAL PSS` value for startup, lesson/audio loaded, speech model
loaded, and translation completed. Use those measured values in the SIH
submission instead of estimates.

## Repository map

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI API, SQLite access, Vosk and IndicTrans2 adapters |
| `frontend/` | Static Capacitor classroom app and Android project |
| `data/` | Seed curriculum content |
| `scripts/` | ONNX export/INT8 and desktop inference checks |
| `requirements.txt` | Python dependencies |
| `README.md` | Project overview and setup |
| `BUILD_GUIDE.md` | Original offline/2GB validation plan |
