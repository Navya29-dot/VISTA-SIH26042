# VISTA — Frontend (SIH 2026 Judge Demo)

`index.html` is a single self-contained page (no build step, no dependencies to install).
Open it directly in any browser, or serve it:

    python3 -m http.server 8000

Then visit http://localhost:5173

## Android emulator

```bash
npm install
npx cap add android
npx cap sync android
npx cap open android
```

The bundled Science Hindi and Santali recordings work without the backend.
For the live voice bridge in the Android emulator, set
`window.VISTA_API_BASE` to `http://10.0.2.2:8000`.

## What's inside
- Hero + pitch stage: 3D floating "antigravity" node network (Three.js, loaded from CDN)
- Interactive tablet mockup with 7 screens: Home, Start a lesson, Teaching mode,
  Understanding Pulse, Re-teach, Bilingual worksheet, and **Ask VISTA**
- Ask VISTA: student selects (or "speaks") a question from an approved phrase bank,
  gets an explanation in the selected mother tongue with synced subtitles running
  down the side of the screen, alongside a Hindi gloss line
- "Why this survives the real device" section — the offline/anti-glassmorphism
  rules from the product blueprint, shown as a judge-facing checklist

## Known placeholder content
- The Santali (Ol Chiki) lines are illustrative placeholder translations for the
  demo only — swap in your human-reviewed, approved translations before presenting.
- Science Hindi and Santali WAV recordings are bundled in `audio/`.
