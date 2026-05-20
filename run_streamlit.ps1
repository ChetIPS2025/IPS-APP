# LEGACY HELPER — starts the ONE unified IPS app (same as: streamlit run app/main.py)
# Not a separate application. See LAUNCHERS.md and README.md.
Set-Location $PSScriptRoot
Write-Host ""
Write-Host "IPS Operations (unified app)"
Write-Host "Root: $(Get-Location)"
Write-Host "Command: streamlit run app/main.py"
Write-Host ""
& streamlit run app/main.py
