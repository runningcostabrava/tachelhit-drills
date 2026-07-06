@echo off
REM Download a YouTube video on THIS computer, then let Render turn it into drills.
REM One-time setup:  pip install yt-dlp requests   (and install ffmpeg)
setlocal
set "URL=%~1"
if "%URL%"=="" set /p URL=Enganxa l'URL de YouTube:
python "%~dp0capture_youtube.py" "%URL%" %2 %3 %4 %5
echo.
pause
