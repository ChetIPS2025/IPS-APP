# IPS APP — run Streamlit from repo root so Python loads app\pages\estimates.py etc.
Set-Location $PSScriptRoot
Write-Host ""
Write-Host "IPS APP root (cwd): $(Get-Location)"
Write-Host "Starting: streamlit run app/main.py"
Write-Host ""
& streamlit run app/main.py
