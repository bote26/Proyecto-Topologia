# Lanza el dashboard usando Python 3.14 (donde están instaladas las deps TDA).
# Uso:  .\run_dashboard.ps1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
py -3.14 -m streamlit run dashboard/app.py
