#!/bin/bash
# Launcher script for Intelligent Recruiter Search UI

echo "=================================="
echo "Intelligent Recruiter Search UI"
echo "=================================="
echo ""

# Check if FastAPI is running
echo "Checking if FastAPI is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ FastAPI is already running on port 8000"
else
    echo "✗ FastAPI is not running"
    echo ""
    echo "Starting FastAPI in background..."
    cd /mnt/c/Users/prita/Downloads/SuperLinked
    nohup python3 scripts/api/search_api.py > logs/api.log 2>&1 &
    API_PID=$!
    echo "✓ FastAPI started (PID: $API_PID)"
    echo "  Logs: logs/api.log"
    echo ""
    echo "Waiting for API to be ready..."
    sleep 5
fi

echo ""
echo "Starting Streamlit UI..."
echo "=================================="
echo ""

cd /mnt/c/Users/prita/Downloads/SuperLinked
streamlit run scripts/ui/recruiter_dashboard.py

echo ""
echo "✓ UI closed"
