Set-Location $PSScriptRoot
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
python -m antecipe.servidor
