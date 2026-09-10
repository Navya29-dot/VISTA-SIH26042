# Hindi-to-Santali Speech Options

## Current Prototype Path

```text
Teacher Hindi speech
  -> Vosk offline Hindi ASR
  -> IndicTrans2 Hindi/Santali text translation
  -> Santali text display
  -> bundled reviewed audio or Santali TTS when available
```

## Practical Sources

1. AI4Bharat IndicTrans2
   - Use for Hindi/Santali text translation.
   - Your backend already exposes this through `/translate/offline`.

2. Vosk Hindi ASR
   - Use for offline Hindi speech-to-text.
   - Feasible for a desktop/Ubuntu backend and possible for Android packaging with model-size tradeoffs.

3. Bhashini
   - Useful connected source for Indian-language ASR, translation, and TTS.
   - Bhashini model listings include Santali in translation/ASR areas and Santali TTS in Devanagari-script support.

4. Santali TTS packages
   - `santali-textts` exists as a beta package, but its own description says vocabulary is limited.
   - For classroom reliability, use reviewed recorded Santali audio for high-frequency lines while collecting more speech data.

## Recommendation

For the SIH prototype, present a hybrid route:

- Free-text typed Hindi: IndicTrans2.
- Spoken Hindi: Vosk plus IndicTrans2.
- Santali audio: reviewed clips for lesson packs and common commands.
- Future production: Santali TTS fine-tuning using school-domain recordings.

This is feasible and honest. It solves the classroom barrier for prepared FLN content immediately, then improves toward full voice-to-voice translation as Santali speech resources improve.
