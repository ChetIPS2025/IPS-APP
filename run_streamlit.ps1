# LEGACY HELPER — starts the ONE unified IPS app (same as: streamlit run app/main.py)
# Not a separate application. See LAUNCHERS.md and README.md.
Set-Location $PSScriptRoot
Write-Host ""
Write-Host "IPS Operations (unified app)"
Write-Host "Root: $(Get-Location)"
Write-Host "Command: python run_streamlit.py"
Write-Host ""
& python run_streamlit.py
