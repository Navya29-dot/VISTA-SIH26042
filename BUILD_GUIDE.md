# VISTA Offline 2GB Build & Validation Guide

**Golden rule: validate the riskiest assumption before building anything else.**
Everything in your pitch rests on one claim — IndicTrans2-200M runs comfortably
on a 2GB Android device. Prove that in Phase 1, on real hardware, before you
invest days wiring up the full app. If it doesn't hold, you want to know on
day 1, not the night before submission.

---

## Phase 1 — Prove the on-device translation model fits (do this first, 1-2 days)

### 1.1 Set up a clean environment (on your laptop)
```bash
python3 -m venv vista-env
source vista-env/bin/activate
pip install "optimum[onnxruntime]" transformers sentencepiece onnxruntime torch
```

### 1.2 Get the right IndicTrans2 variant
Hindi → Santali is an **indic-to-indic** translation, not en-indic. Go to
AI4Bharat's Hugging Face org (`huggingface.co/ai4bharat`) and find the
**distilled indic-indic** checkpoint — confirm the exact repo name and
parameter count yourself on the model card before you commit to it in your
slides; sizes/names do get updated, and I can't fetch that page live from here.

### 1.3 Export to ONNX and quantize to INT8
Use `export_indictrans2_onnx.py` (attached below) as your starting point.
It exports the HF model to ONNX and applies dynamic INT8 quantization —
adjust the model ID once you've confirmed it in step 1.2.

### 1.4 Measure real desktop RAM first (sanity check, 10 minutes)
```bash
/usr/bin/time -v python3 run_inference_test.py 2>&1 | grep "Maximum resident"
```
This won't match Android exactly, but if it's already over ~500MB resident
on a desktop with a clean process, that's an early warning sign.

### 1.5 Measure the number that actually matters: on an Android device or a
hard-capped emulator
1. In Android Studio → AVD Manager → create a device, set **RAM: 2048MB** explicitly.
2. Add `onnxruntime-android` as a Gradle dependency in a throwaway test app.
3. Load the quantized model, run one translation, then read:
```bash
adb shell dumpsys meminfo <your.test.package>
```
Look at the **TOTAL PSS** line. That's your real number — the one you put
on the slide, replacing "measured budget, not a guess" with an actual value.

**Decision point:** if this comes in under ~400MB, you're in good shape.
If it's closer to 800MB-1GB+, you still have budget (Android+WebView ~700MB
target leaves ~1.3GB), but you should re-test with the phrase bank and Vosk
loaded simultaneously, since they all compete for the same 2GB.

---

## Phase 2 — Offline authoring pipeline with Ollama (2-3 days)

### 2.1 Install Ollama locally
```bash
# On your authoring laptop/server (NOT the Android device — Ollama doesn't run on Android)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b     # or mistral:7b if your laptop has less RAM/GPU
ollama serve                # runs a local REST API on localhost:11434
```

### 2.2 Wire it into your FastAPI authoring backend
```python
import httpx

async def draft_lesson(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.1:8b", "prompt": prompt, "stream": False},
        )
        return resp.json()["response"]
```
This replaces your Groq call. Same interface, zero cloud dependency, zero
internet required once the model is pulled.

### 2.3 Keep IndicTrans2 (the larger, higher-quality variant) self-hosted
locally too for authoring-time translation drafts — same machine, same
principle: pulled once, runs offline forever after.

### 2.4 Human review stays exactly as designed
Native-speaker review UI → approve/edit → export to your SQLite + audio
content pack. Nothing changes here.

---

## Phase 3 — Classroom app offline runtime (Android, Capacitor) (1-2 weeks)

1. **Bundle or first-sync-then-cache** the phrase bank, quantized ONNX
   model, and Vosk small Hindi model as app assets.
2. **Bridge onnxruntime-mobile into Capacitor**: since your frontend is
   React+Capacitor, native inference needs a small Kotlin/Java Capacitor
   plugin exposing a `translate(text: string): Promise<string>` method to JS.
   Capacitor's plugin docs (`capacitorjs.com/docs/plugins/android`) walk
   through this — it's the one piece of native Android code you can't avoid.
3. **Retrieval-first order of operations** in the plugin logic:
   `phrase bank exact/fuzzy match → if no match, call ONNX IndicTrans2 →
   cache the result back into the phrase bank for next time.`
   This keeps the model invocation rare, which is good for both RAM and battery.
4. **Vosk Android integration** follows the same plugin pattern
   (`alphacep/vosk-android-demo` on GitHub is the standard reference).
5. **Test with the device in airplane mode, full stop.** Not "low signal" —
   airplane mode. That's the test a judge would run if they were skeptical,
   so run it yourself first.

---

## Phase 4 — Offline TTS (treat as a stretch goal, not a submission blocker)

1. Your native-speaker recordings from the review pipeline are already your
   primary audio bank — this alone covers most classroom content and needs
   **zero AI**.
2. For the fallback (novel text), Piper is the easier on-ramp for a student
   team: `github.com/rhasspy/piper` has an open training recipe. Realistically
   needs a few hours of clean, transcribed single-speaker audio to produce a
   usable ~20-60MB voice model. This is genuinely a multi-day training task —
   plan it as a "we are building X, here's our training plan" claim for this
   round, and an actual working demo for the next round if you advance.

---

## Phase 5 — Prove it, don't just claim it

1. Capture `adb shell dumpsys meminfo` output as a screenshot — put the real
   number on your slide.
2. Record a 30-60 second screen capture: airplane mode on, teacher speaks a
   Hindi sentence, VISTA translates and plays Santali audio, fully offline.
   This single clip is worth more than any bullet point in your deck.
3. Update the RAM budget line on slide 4 from an estimate to a measured result.

---

## What to do first, this week
1. Phase 1.1-1.3 (export + quantize) — no device needed, just your laptop.
2. Phase 1.5 (the emulator/device test) — this is the number that either
   validates or breaks your whole pitch. Do it before writing another line
   of app code.
3. Only then move to Phase 2 and 3 in parallel if you have team members to split the work.
