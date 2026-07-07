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

## Hands-off mode: the background AGENT (recommended)
Instead of running a command per video, run the **agent** once and then just use
the web app. The agent watches Render for URLs you queue and downloads them
automatically on your IP.

**One-time setup:** `pip install yt-dlp requests` + ffmpeg on PATH.

**Start it:**
- Double-click **`capture_agent.bat`** (a window stays open showing activity), or
- For silent auto-start at login: put a shortcut to **`start_agent_hidden.vbs`**
  in your Startup folder — press `Win+R`, type `shell:startup`, drop the shortcut
  there. Now it runs invisibly every time you log in.

**Then:** in the web app's *Captura* screen, paste a YouTube URL and submit. The
agent downloads it and Render makes drills — you don't touch anything else.

(The one-shot `capture.bat` above still works too, if you prefer per-video.)

## Config (optional)
- `TACHELHIT_API` — backend URL (defaults to the Render one)
- `TACHELHIT_API_KEY` — only if the backend enforces `X-API-Key`
- `CAPTURE_POLL_SECS` — agent poll interval (default 8)

## Notes
- Still needs the **ASR + translation Spaces awake** on HuggingFace (that's the
  work the server does). Keep them running / deploy the consolidated NLP Space.
- Nothing is uploaded to YouTube or anywhere except your own Render backend.
