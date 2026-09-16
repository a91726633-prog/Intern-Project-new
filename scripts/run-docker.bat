@echo off
cd /d "%~dp0.."
echo Starting full app with Docker Compose...
echo Frontend will open at http://localhost:5173
echo Backend docs will open at http://localhost:8000/docs
docker compose up --build
