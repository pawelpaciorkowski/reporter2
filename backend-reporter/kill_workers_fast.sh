#!/bin/bash

echo "Fast killing all reporter workers..."

# Kill all screen sessions containing repworker
screen -wipe >/dev/null 2>&1

# Get all repworker screen names and kill them in parallel
screen -ls | grep repworker | cut -d. -f1 | xargs -I {} -P 20 screen -X -S {} quit 2>/dev/null

# Wait a bit
sleep 2

# Force kill any remaining processes
pkill -f "rq worker.*repworker" 2>/dev/null

# Kill any remaining screen sessions
screen -ls | grep repworker | cut -d. -f1 | xargs -I {} kill -9 {} 2>/dev/null

echo "All workers killed. You can now run restart_workers.py or restart_workers_fast.py" 