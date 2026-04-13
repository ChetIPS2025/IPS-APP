@echo off
REM IPS APP — always run Streamlit from this folder so imports resolve to app\...
cd /d "%~dp0"
echo.
echo IPS APP root (cwd): %CD%
echo Starting: streamlit run app\main.py
echo.
streamlit run app/main.py
