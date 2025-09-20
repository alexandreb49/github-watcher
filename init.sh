#!/bin/bash

python3 -m venv python-env

echo "Initiating the virtual environment"

#work only on linux
source python-env/bin/activate

pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8080 --reload