# VISTA Demo Guide

## What is AI-assisted in this prototype

VISTA is AI-assisted in three layers:

1. Content preparation: Hindi FLN lesson text can be translated and reviewed before school deployment, then packed into the offline app.
2. Free-text classroom translation: when the local Ubuntu backend is running, the Android/emulator app calls `/translate/offline`, which uses IndicTrans2 for Hindi-to-Santali translation.
3. Classroom fallback: if the backend is unreachable, the Android app uses an approved local phrase/domain pack to match common teacher utterances, show Santali text, speak it when a Santali-capable system voice is available, and measure sub-3-second local response time.

The current classroom prototype is honest offline AI assistance. Typed Hindi can be translated through the local IndicTrans2 backend; unrestricted spoken Hindi depends on offline Hindi ASR being available in the emulator/device.

## Important limitation

The included Hindi lesson audio (`audio/Science.wav`) and Santali lesson audio (`audio/Science santali.wav`) are fixed clips. That is acceptable for lesson-script playback, flashcards, and prepared curriculum content.

For real classroom voice-to-voice translation where the teacher can say anything and Santali audio returns within 3 seconds, the production system still needs:

- Hindi offline ASR, such as Vosk, Whisper.cpp, or Android SpeechRecognizer with offline Hindi packs where available.
- Hindi-to-Santali translation, either IndicTrans-style model support if available or a trained domain model using parallel Hindi-Santali FLN sentences.
- Santali TTS or approved phrase-level neural/audio units. If no open Santali TTS is available, the practical path is to ship approved recorded/generative audio for classroom phrases and lesson packs.
- A fallback approved phrase bank for safety when the model confidence is low.

## What to show in the demo video

1. Open the Android app in emulator.
2. Go to Teaching mode.
3. Tap the phrase buttons in Live classroom translator and show Santali text appears instantly.
4. Type a new Hindi sentence and tap Translate now while the Ubuntu IndicTrans2 backend is running; show that the text is not limited to the phrase buttons.
5. Play the prepared Hindi lesson audio and show Santali lesson audio/text.
6. Go to Worksheet and generate a bilingual FLN worksheet plus flashcards.
7. Turn off internet in the emulator and repeat the phrase translation and worksheet generation.

## Data you should add before final submission

Add more data. The judge will expect coverage beyond one plant lesson.

Minimum useful dataset:

- 300 to 500 Hindi-Santali classroom phrases: greetings, instructions, praise, correction, group work, safety, questions.
- 100 to 150 FLN lesson scripts across literacy, numeracy, and EVS.
- 500 to 1,000 bilingual word/phrase pairs with Santali in Ol Chiki and a Hindi gloss.
- 50 to 100 NIPUN Bharat outcome mappings.
- Recorded or generated audio for the most common 200 to 300 Santali lines.

Best prototype strategy: make Santali complete first. Mention Ho and Mundari as the same pipeline with language packs, but do not pretend all three are equally ready.

## Emulator run steps

From this folder:

```powershell
npm.cmd run cap:prepare
npm.cmd run cap:sync
cd android
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat --no-daemon assembleDebug
```

If the build fails with `The paging file is too small`, close Android Studio/Chrome/other heavy apps or increase Windows virtual memory, then rerun the last command.

After the APK builds:

```powershell
.\gradlew.bat installDebug
```

Or open `android` in Android Studio and press Run with an emulator selected.
