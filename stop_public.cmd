@echo off
cd /d "%~dp0"
if not exist outputs mkdir outputs
echo stop>outputs\public-stop.flag
echo Public link is stopping.
