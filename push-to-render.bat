@echo off
REM Commit the updated capstone and push it, which triggers Render's auto-deploy.
REM Double-click this file, or run it from a terminal in the repo folder.
setlocal
cd /d "%~dp0"

echo.
echo === Capital Markets Agentic Capstone - push to GitHub ===
echo Folder: %cd%
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo ERROR: this folder is not a git repository.
  pause
  exit /b 1
)

echo Files changed:
git status --short
echo.

git add -A
REM This helper script is a local convenience, not part of the project.
git reset -- push-to-render.bat >nul 2>&1

git diff --cached --quiet
if not errorlevel 1 (
  echo Nothing to commit - the repository already matches the new code.
  echo.
  pause
  exit /b 0
)

git commit -F - <<COMMITMSG
Add custom-domain support, brand logo, RAG document uploads, and the executable IEEE 829 suite

- QTCAP_CANONICAL_HOST / QTCAP_ALLOWED_HOSTS for serving from a custom subdomain
- GenAItesting.online logo, favicons and brand palette in the console
- Per-browser document corpus with the IN-07 document guard (flag, never block)
- 317-case IEEE 829 workbook made executable, writing results back into the sheet
- 455 tests green; the IEEE workbook deliberately is not

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01ShZpJiwPFdnzDr7xyDELsG
COMMITMSG

if errorlevel 1 (
  echo.
  echo ERROR: the commit failed. Nothing was pushed.
  pause
  exit /b 1
)

echo.
echo Pushing...
git push
if errorlevel 1 (
  echo.
  echo ERROR: the push failed - check the message above ^(credentials, or a branch behind the remote^).
  pause
  exit /b 1
)

echo.
echo Pushed. Render will start building within about a minute:
echo   https://dashboard.render.com
echo   https://capital-markets-agentic-capstone.onrender.com
echo.
pause
