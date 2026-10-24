cd "$(dirname "$0")"
python -m pip install -r requirements.txt
export PYTHONPATH=src
python -m antecipe.servidor
