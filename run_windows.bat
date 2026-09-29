@echo off
cd /d "%~dp0"
echo ==============================================
echo        NDL Studio LOCAL BROADCAST
 echo ==============================================
if not exist .venv (
    echo Creating virtual environment...
    py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
pause
