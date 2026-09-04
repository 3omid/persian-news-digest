@echo off
chcp 65001 >nul
echo ============================================
echo   Push Persian News Digest to GitHub
echo ============================================
echo.

REM --- Check if git is installed ---
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git is not installed on this computer.
    echo Please install it first from: https://git-scm.com/download/win
    echo Then run this file again.
    pause
    exit /b 1
)

REM --- Go to the folder this .bat file is sitting in ---
cd /d "%~dp0"
echo Current folder: %cd%
echo.

REM --- Init repo if needed ---
if not exist ".git" (
    echo Initializing new git repo...
    git init
    git branch -M main
)

REM --- Check if 'origin' remote is actually configured (regardless of .git existing) ---
git remote get-url origin >nul 2>nul
if errorlevel 1 (
    echo No GitHub remote is linked to this folder yet.
    set /p REPO_URL="Paste your GitHub repo URL (e.g. https://github.com/3omid/persian-news-digest.git): "
    git remote add origin "%REPO_URL%"
) else (
    echo GitHub remote already linked:
    git remote get-url origin
)

echo.
echo Adding all files (including hidden .github folder)...
git add -A

echo.
set /p COMMIT_MSG="Commit message (or press Enter for default): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Update news digest project

git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo Nothing new to commit, continuing to push anyway...
)

echo.
echo Pushing to GitHub (force push to make sure it matches this folder exactly)...
git push -u origin main --force

if errorlevel 1 (
    echo.
    echo ============================================
    echo   PUSH FAILED. Common reasons:
    echo   - Wrong repo URL was entered
    echo   - Login/authorization was cancelled
    echo   Run this file again to retry.
    echo ============================================
) else (
    echo.
    echo ============================================
    echo   Done! Check github.com to confirm.
    echo ============================================
)
pause
