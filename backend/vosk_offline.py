from __future__ import annotations

import io
import json
import wave
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from backend.config import get_settings


@lru_cache(maxsize=2)
def _load_model(language_code: str) -> Any:
    settings = get_settings()
    model_path = (
        settings.vosk_english_model_path
        if language_code == "en-IN"
        else settings.vosk_model_path
    )
    if not model_path:
        raise RuntimeError(
            f"No Vosk model is configured for {language_code}. Set "
            f"{'VOSK_ENGLISH_MODEL_PATH' if language_code == 'en-IN' else 'VOSK_MODEL_PATH'} "
            "to an extracted model folder in .env."
        )
    if not Path(model_path).is_dir():
        raise RuntimeError(
            f"Vosk model folder does not exist for {language_code}: {model_path}"
        )
    try:
        from vosk import Model
    except ImportError as exc:
        raise RuntimeError(
            "The Vosk package is missing. Install it with: python -m pip install vosk"
        ) from exc
    try:
        return Model(model_path)
    except Exception as exc:
        raise RuntimeError(
            f"Vosk could not load the model at {model_path}. "
            "Point VOSK_MODEL_PATH to the folder containing am, conf, graph, "
            "ivector, and rescore."
        ) from exc


async def transcribe_wav(file: UploadFile, language_code: str = "hi-IN") -> dict[str, str | float]:
    content = await file.read()
    

    try:
        with wave.open(io.BytesIO(content), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())
    except (wave.Error, EOFError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Offline Vosk expects a PCM WAV file (mono, 16-bit, 16 kHz).",
        ) from exc

    if channels != 1 or sample_width != 2:
        raise HTTPException(status_code=400, detail="WAV must be mono and 16-bit PCM.")

    settings = get_settings()
    if frame_rate != settings.vosk_sample_rate:
        raise HTTPException(
            status_code=400,
            detail=f"WAV must use {settings.vosk_sample_rate} Hz; received {frame_rate} Hz.",
        )

    try:
        from vosk import KaldiRecognizer

        if language_code not in {"hi-IN", "en-IN"}:
            raise HTTPException(
                status_code=400,
                detail="Offline Vosk supports hi-IN and en-IN in this setup.",
            )
        recognizer = KaldiRecognizer(_load_model(language_code), float(frame_rate))
        recognizer.AcceptWaveform(frames)
        result = json.loads(recognizer.FinalResult())
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=f"Offline Vosk transcription failed: {exc}") from exc

    return {
        "text": str(result.get("text", "")).strip(),
        "language_code": language_code,
        "engine": "vosk",
        "offline": True,
    }
