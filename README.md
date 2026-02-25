# Tachelhit Drills - Detailed Application Workflow

Tachelhit Drills is a comprehensive, full-stack application designed for learning the Tachelhit language, using Catalan as a reference. It allows users to create, manage, and practice with interactive language drills, group them into tests, and automatically generate video content for review.

## Core Features

-   **Drill & Test Management:** Create, update, and delete language "drills" (individual lessons) and group them into "tests".
-   **Interactive Drill Player:** Practice with drills in a dedicated player featuring:
    -   **Custom Audio Playback:** For each drill, the Catalan TTS audio plays once, followed by the Tachelhit recorded audio playing twice.
    -   **Looping Mode:** An option to continuously loop through the sequence of drills for extended practice.
-   **Tamazight ASR & Semantic Correction:** Transcribe Tachelhit voice into text with high accuracy:
    -   **Acoustic Transcription:** Uses `OpenAI Whisper` (running on CPU) for a rough phonetic transcription.
    -   **DeepSeek Correction:** Uses the `DeepSeek API` to map the rough transcription to a user-curated dataset of known phrases.
    -   **Custom Dataset Selection:** Users can select which drills (Tachelhit-Catalan pairs) are used to "train" the correction layer.
-   **Audio Trimming Tool:** Fix recordings directly in the browser by trimming silence or errors using MoviePy on the backend.
-   **Automated Video Generation:** Offload the creation of video content to a dedicated microservice:
    -   **Shorts:** Generate vertical videos for individual drills.
    -   **Demos:** Generate horizontal videos that simulate a user interacting with the Drill Player for an entire test, including the custom audio playback sequence.
-   **Cloud Media Storage:** All user-uploaded media, synthesized audio, and generated videos are automatically stored in Cloudinary for persistent, global access.

## Application Architecture & Information Flow

This application is built with a modern, decoupled three-part architecture. Understanding the flow of information between these components is key to understanding the application.

1.  **Frontend (React/Vite on Vercel)**
    -   **Location:** `frontend/`
    -   **Description:** The user-facing interface. It handles all user interactions and renders the application's main pages.
    -   **Key Pages/Views:**
        -   `DrillsGrid`: The main dashboard for viewing all drills.
        -   `TestsDashboard`: A view for managing tests, generating demo videos, and initiating practice sessions.
        -   `DrillPlayer`: The interactive component for practicing a sequence of drills.
        -   `TestTaking`: The interface for taking a formal test.
    -   **Deployment:** Deployed on Vercel.

2.  **Backend (FastAPI/Python on Render)**
    -   **Location:** `backend/`
    -   **Description:** A robust API that serves as the application's central hub. It manages all data via a PostgreSQL database, handles business logic, and orchestrates long-running tasks.
    -   **Deployment:** Deployed on Render.

3.  **Video Generation Service (Python/MoviePy on HuggingFace Space)**
    -   **Location:** `huggingface-space/`
    -   **Description:** A dedicated microservice that handles the CPU-intensive task of video creation using MoviePy.
    -   **Deployment:** Deployed as a HuggingFace Space.

4.  **Media Storage (Cloudinary)**
    -   **Description:** A cloud-based service used to store all media assets, including images, user-recorded audio, synthesized TTS audio, and generated videos. This ensures media is accessible by all parts of the application.

---

## Detailed Workflows

### Catalan TTS Synthesis on Drill Update
1.  **Action:** A user modifies the "Catalan" text of a drill in the frontend UI.
2.  **API Call:** The frontend sends a `PUT` request to the `/drills/{drill_id}` endpoint on the Render backend.
3.  **Backend Logic:**
    -   The `update_drill` function in `backend/main.py` detects the change to `text_catalan`.
    -   It calls the `generate_catalan_tts` function.
    -   `generate_catalan_tts` uses the `gtts` library to create an MP3 file of the Catalan speech.
4.  **Cloudinary Upload:**
    -   The backend uploads this newly created MP3 file directly to the `tachelhit/tts` folder in Cloudinary.
5.  **Database Update:**
    -   The backend receives the permanent, secure URL for the audio file from Cloudinary.
    -   It saves this URL to the `audio_tts_url` column of the corresponding drill in the PostgreSQL database.

### Demo Video Generation
This is the most complex workflow, involving all components of the system.

1.  **User Action (Vercel):** A user clicks the "Generate Demo Video" button for a specific test on the `TestsDashboard` page.
2.  **API Request (Vercel -> Render):** The frontend sends a `POST` request to the `/generate-drillplayer-demo/{test_id}` endpoint on the Render backend.
3.  **Backend Orchestration (Render):**
    -   The `generate_drillplayer_demo` function in `backend/main.py` receives the request.
    -   It gathers all necessary data for each drill in the test (including `text_catalan`, `text_tachelhit`, `text_arabic`, `image_url`, `audio_url`, `audio_tts_url`) from its PostgreSQL database.
    -   It packages this data into a JSON payload.
    -   It starts a background task (`background_video_vault`) to handle the long-running process.
    -   It **immediately** responds to the frontend with a `{"status": "processing"}` message, preventing a browser timeout.
4.  **Video Generation Request (Render -> HuggingFace):**
    -   The `background_video_vault` task running on Render sends a `POST` request to the `predict` endpoint of the HuggingFace Space, passing the JSON payload with all the drill data.
5.  **Video Processing (HuggingFace):**
    -   The `app.py` on the HuggingFace Space receives the data and calls the `generate_drillplayer_demo` function in `shorts_generator.py`.
    -   This script iterates through each drill:
        -   It downloads the `audio_tts_url` (Catalan) and `audio_url` (Tachelhit) from their Cloudinary URLs.
        -   It uses `moviepy` to create a new audio clip: **Catalan audio (1x) + Tachelhit audio (2x)**.
        -   It generates a static image simulating the `DrillPlayer` UI.
        -   It combines the image and the new composite audio track into a short video clip for that drill.
    -   After processing all drills, it concatenates all individual video clips into one final demo video.
    -   It saves this video to a temporary local path on the HuggingFace Space and returns this temporary path in its response to the Render backend.
6.  **Video Vaulting (Render -> Cloudinary):**
    -   The `background_video_vault` task on Render receives the temporary video path from HuggingFace.
    -   It instructs Cloudinary to upload the video directly from the HuggingFace URL.
7.  **Database Update (Render):**
    -   Cloudinary provides a permanent, secure URL for the newly uploaded video.
    -   The `background_video_vault` task updates the `video_url` field for the corresponding `Test` in the PostgreSQL database.
8.  **Polling and Display (Vercel -> Render):**
    -   Meanwhile, after receiving the initial "processing" status, the frontend UI has started periodically polling the `/tests/{test_id}` endpoint on the Render backend every 10 seconds.
    -   Once the database is updated (step 7), the response to this `GET` request will contain the permanent Cloudinary `video_url`.
    -   The frontend sees the new URL, stops polling, and displays the "Demo Video Ready!" section with the embedded video player.

---

## Local Development Setup & Deployment

For instructions on setting up the local development environment for each service and for deployment information, please refer to the "Local Development Setup" section above in this document.

## Local Tools for Aider/DeepSeek Development

This project includes a set of local tools to capture the state of the web application for easier debugging and development with AI assistants. For detailed instructions, please see the `local_tools/README.md` file.
