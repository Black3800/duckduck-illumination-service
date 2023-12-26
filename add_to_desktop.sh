#!/bin/sh
xset s noblank
xset s off
xset -dpms
cd ~/duckduck/duckduck-illumination-service
nohup ./.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &
cd ~/duckduck/duckduck-event-listener
nohup ./.venv/bin/python socket-relay.py &
nohup ./.venv/bin/python main.py &
npm run --prefix ~/duckduck/duckduck-clockface preview &
chromium-browser --autoplay-policy=no-user-gesture-required http://localhost:4173/