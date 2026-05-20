@echo off
REM LEGACY HELPER — starts the ONE unified IPS app (same as: streamlit run app/main.py)
REM Not a separate application. See LAUNCHERS.md and README.md.
cd /d "%~dp0"
echo.
echo IPS Operations (unified app)
echo Root: %CD%
echo Command: python run_streamlit.py
echo.
python run_streamlit.py
