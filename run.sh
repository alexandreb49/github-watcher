#!/bin/bash

python3 -m venv python-env

echo "Initiating the virtual environment"

source python-env/bin/activate

pip install -r requirements.txt

ngrok config add-authtoken $NGROK_AUTHTOKEN

ngrok http 8080 --region=eu --hostname=$NGROK_DOMAIN &

# Run on port 8080 as your user (not root)
uvicorn main:app --host 0.0.0.0 --port 8080 --reload 

