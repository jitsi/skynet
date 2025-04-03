#!/bin/bash

echo "Starting health check polling for localhost:8001/healthz"
echo "Press Ctrl+C to stop"
echo "----------------------------------------"

while true; do
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    response=$(curl -s -o /dev/null -w "%{http_code}" \
               --connect-timeout 1 \
               --max-time 2 \
               localhost:8001/healthz)
    
    if [ "$response" = "200" ]; then
        echo "[$timestamp] Health check: OK (Status: $response)"
    else
        echo "[$timestamp] Health check: FAILED (Status: $response)"
    fi
    
    sleep 1
done
