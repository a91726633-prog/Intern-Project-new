@echo off
cd /d "%~dp0"
echo ================================================
echo Async Document Workflow Internship Project
echo ================================================
echo.
echo This will start:
echo - PostgreSQL
echo - Redis
echo - FastAPI backend
echo - Celery worker
echo - React frontend
echo.
echo Open Docker Desktop first, then press any key.
pause
docker compose up --build
