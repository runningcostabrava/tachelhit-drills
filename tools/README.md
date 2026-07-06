# Local capture — download on your computer, process on Render

YouTube blocks `yt-dlp` from Render's datacenter IP, so URL capture in the app
often fails. This helper does the **download on your own computer** (your home
IP isn't blocked) and then hands the file to Render, which does the rest
server-side: **transcribe → correct → translate → create drills**. The drills
appear in the app's Drills list.

## One-time setup
```
pip install yt-dlp requests
```
Also install **ffmpeg** and make sure it's on your PATH (needed to extract audio).

## Use it
Double-click **`capture.bat`** and paste a URL, or from a terminal:
```
python capture_youtube.py "https://www.youtube.com/watch?v=XXXX"
```
Options:
```
python capture_youtube.py "<url>" --tag lesson1 --lang shi --audio-only
```
- `--tag`  tag to put on the created drills
- `--lang` ASR language hint (e.g. `shi`)
- `--audio-only` download just the audio (faster; use when you don't need the video clip)

It downloads, uploads to Render, then prints progress
(`TRANSCRIBING → CORRECTING → TRANSLATING → CREATING_DRILLS`) until it reports
`drills_created`. Then open the app and review them.

## Config (optional)
- `TACHELHIT_API` — backend URL (defaults to the Render one)
- `TACHELHIT_API_KEY` — only if the backend enforces `X-API-Key`

## Notes
- Still needs the **ASR + translation Spaces awake** on HuggingFace (that's the
  work the server does). Keep them running / deploy the consolidated NLP Space.
- Nothing is uploaded to YouTube or anywhere except your own Render backend.
