from __future__ import annotations

import json
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.config import get_settings


INDICTRANS_LANGUAGE_CODES = {
    "en-IN": "eng_Latn",
    "en": "eng_Latn",
    "hi-IN": "hin_Deva",
    "hi": "hin_Deva",
    "sat": "sat_Olck",
    "sat-IN": "sat_Olck",
}


def _device_name() -> str:
    import torch

    configured = get_settings().indictrans2_device
    if configured != "auto":
        return configured
    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=1)
def _load_pipeline() -> tuple[Any, Any, Any, str, Any]:
    """Load the local model once; model files are cached by Hugging Face."""
    try:
        import torch
        import transformers.tokenization_utils as tokenization_utils
        import transformers

        # IndicTransToolkit 1.1.1 imports this symbol from an older Transformers
        # module path; newer Transformers still exports it at the package root.
        if not hasattr(tokenization_utils, "PreTrainedTokenizerBase"):
            tokenization_utils.PreTrainedTokenizerBase = transformers.PreTrainedTokenizerBase
        from IndicTransToolkit import IndicProcessor
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "Offline translation dependencies are missing. "
            "Install requirements.txt before using /translate/offline."
        ) from exc

    settings = get_settings()
    model_kwargs: dict[str, Any] = {
        "trust_remote_code": True,
        "local_files_only": settings.indictrans2_local_files_only,
    }
    if settings.indictrans2_cache_dir:
        model_kwargs["cache_dir"] = settings.indictrans2_cache_dir

    tokenizer = AutoTokenizer.from_pretrained(settings.indictrans2_model_name, **model_kwargs)
    model = AutoModelForSeq2SeqLM.from_pretrained(settings.indictrans2_model_name, **model_kwargs)
    device = _device_name()
    model.to(device)
    model.eval()
    return tokenizer, model, IndicProcessor(inference=True), device, torch


def translate(text: str, source_language_code: str, target_language_code: str) -> dict[str, str]:
    source = INDICTRANS_LANGUAGE_CODES.get(source_language_code)
    target = INDICTRANS_LANGUAGE_CODES.get(target_language_code)
    if not source or not target:
        raise HTTPException(
            status_code=400,
            detail=(
                "IndicTrans2 supports English and Santali in this setup. "
                "Use en-IN/en or sat/sat-IN."
            ),
        )
    if source == target:
        return {
            "translated_text": text,
            "source_language_code": source_language_code,
            "target_language_code": target_language_code,
            "engine": "indictrans2",
        }

    try:
        phrase_match = _phrase_bank_match(text)
        if phrase_match:
            return {
                "translated_text": phrase_match,
                "source_language_code": source_language_code,
                "target_language_code": target_language_code,
                "engine": "phrase-bank",
            }
        tokenizer, model, processor, device, torch = _load_pipeline()
        batch = processor.preprocess_batch(
            [text],
            src_lang=source,
            tgt_lang=target,
            visualize=False,
        )
        inputs = tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(device)
        with torch.inference_mode():
            generated_tokens = model.generate(
                **inputs,
                use_cache=True,
                max_length=256,
                num_beams=5,
                num_return_sequences=1,
            )
        decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        result = processor.postprocess_batch(decoded, lang=target)
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"IndicTrans2 translation failed: {exc}") from exc

    return {
        "translated_text": result[0],
        "source_language_code": source_language_code,
        "target_language_code": target_language_code,
        "engine": "indictrans2",
    }


def _phrase_bank_match(text: str) -> str | None:
    path = get_settings().phrase_bank_path
    if not path:
        return None
    phrase_file = Path(path)
    if not phrase_file.is_file():
        return None
    entries = json.loads(phrase_file.read_text(encoding="utf-8"))
    if not isinstance(entries, dict):
        raise ValueError("PHRASE_BANK_PATH must point to a JSON object of source/translation pairs.")
    normalized = text.strip().casefold()
    exact = next((value for key, value in entries.items() if str(key).strip().casefold() == normalized), None)
    if exact is not None:
        return str(exact)
    matches = get_close_matches(normalized, [str(key).strip().casefold() for key in entries], n=1, cutoff=0.94)
    if matches:
        for key, value in entries.items():
            if str(key).strip().casefold() == matches[0]:
                return str(value)
    return None
