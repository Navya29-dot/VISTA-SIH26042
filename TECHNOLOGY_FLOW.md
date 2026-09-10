# VISTA Technologies and Function Flow

## Technologies Used

| Technology | Function in VISTA |
| --- | --- |
| Android 9+ WebView via Capacitor | Packages the classroom app as an Android APK for low-cost tablets and emulator demos. |
| HTML, CSS, JavaScript | Runs the offline teacher interface, worksheets, flashcards, Understanding Pulse, and fallback translation pack. |
| FastAPI | Backend API for translation, speech bridge, student assessment, curriculum generation, and sync/export endpoints. |
| AI4Bharat IndicTrans2 | Local Ubuntu translation engine for Hindi-to-Santali text translation through `/translate/offline`. |
| Vosk offline ASR | Offline Hindi speech recognition for the `/voice-bridge/offline` classroom voice bridge. |
| Approved phrase/domain packs | Fast on-device fallback for common classroom instructions when the model or internet is unavailable. |
| Web Speech / Android TTS fallback | Attempts target-language audio playback when a compatible voice exists; otherwise uses reviewed audio clips. |
| SQLite export bundle | Future tablet sync format for reviewed translations, worksheets, audio files, and learning-outcome metadata. |
| SQLite | Local database for concepts, questions, translation drafts, approvals, worksheets, and learner attempts. |
| NIPUN Bharat FLN mapping | Aligns lessons, oral checks, worksheets, and pulse evidence to learning outcomes. |

## Translation and Voice Flow

```mermaid
flowchart LR
    A[Teacher speaks or types Hindi] --> B{Input type}
    B -->|Typed| C[Frontend POST /translate/offline]
    B -->|Voice| D[Frontend records audio]
    D --> E[POST /voice-bridge/offline]
    E --> F[Vosk Hindi ASR]
    F --> C
    C --> G[IndicTrans2 Hindi to Santali]
    G --> H[Santali text on tablet]
    H --> I{Audio available?}
    I -->|Reviewed clip| J[Play bundled audio]
    I -->|System TTS| K[Speak with TTS]
    I -->|No voice| L[Show large readable Santali text]
    C -->|Backend unavailable| M[Approved offline phrase pack]
    M --> H
```

## Understanding Pulse Flow

```mermaid
flowchart TD
    A[Teacher asks NIPUN-aligned oral question] --> B[Student responds in Santali]
    B --> C[Teacher selects closest answer or records voice]
    C --> D[Answer scored as Understood, Unsure, or Needs Help]
    D --> E[Pulse updates class percentage, learner evidence, confidence]
    E --> F{Misconception count}
    F -->|0 or 1 learner struggling| G[Continue lesson and sample another learner]
    F -->|2+ learners struggling| H[AI Co-pilot recommends re-teach]
    H --> I[Re-teach tab changes to misconception-specific plan]
    I --> J[Teacher rechecks learners and pulse updates again]
```

## Offline Content Sync Flow

```mermaid
flowchart LR
    A[Backend content preparation] --> B[AI drafts translation and worksheets]
    B --> C[Human review and approval]
    C --> D[Bundle text, audio, worksheets, outcomes]
    D --> E[Initial tablet sync]
    E --> F[Offline classroom use]
    F --> G[Attempts saved locally]
    G --> H[Sync back when internet returns]
```

## Feasible Speech Source Options

| Need | Best source or route |
| --- | --- |
| Hindi offline speech-to-text | Vosk Hindi model or Bhashini/AI4Bharat Hindi ASR during connected preparation. |
| Hindi/Santali translation | AI4Bharat IndicTrans2, plus fine-tuning with FLN Hindi-Santali parallel sentences. |
| Santali TTS | Bhashini lists Santali TTS in Devanagari-script support; `santali-textts` exists but is limited-vocabulary beta. For dependable classroom use, ship reviewed Santali audio clips for high-frequency lines while collecting speech data. |
| Ho and Mundari expansion | Use the same language-pack architecture: glossary, classroom phrases, lesson scripts, recordings, and reviewer approval. |

## Usefulness Assessment

This project does address the tribal-language classroom barrier at prototype level because it helps a Hindi-speaking teacher deliver prepared mother-tongue explanations, ask bilingual checks, generate FLN worksheets, and react to learner confusion without prior Santali training.

The production risk is open-ended speech. For reliable real classrooms, keep the system hybrid: model translation when confident, approved phrase/audio packs for common classroom moments, and human-reviewed curriculum packs for lessons.
