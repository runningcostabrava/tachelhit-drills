@echo off
REM Tachelhit capture agent — leave this window running. It downloads any URL you
REM queue from the web app, on your own IP, and hands it to Render automatically.
REM One-time setup:  pip install yt-dlp requests   (and install ffmpeg)
title Tachelhit capture agent
python "%~dp0capture_agent.py"
pause
