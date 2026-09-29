Set-Location $PSScriptRoot
Write-Host '=============================================='
Write-Host '       NDL Studio LOCAL BROADCAST'
Write-Host '=============================================='
if (-not (Test-Path '.venv')) { py -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
