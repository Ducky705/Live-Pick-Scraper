#!/bin/bash
# start.sh
# Simple wrapper to run and auto-restart the live scraper if it crashes

while true; do
    echo "Starting Live Pick Scraper..."
    python -u live_runner.py
    echo "Scraper crashed. Restarting in 5 seconds..."
    sleep 5
done
