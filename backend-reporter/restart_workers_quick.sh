#!/bin/bash

echo "🚀 Quick Worker Restart Tool"
echo "============================"

cd "$(dirname "$0")"

# Check if we're in the right directory
if [ ! -f "restart_workers.py" ]; then
    echo "❌ Error: Must be run from backend-reporter directory"
    exit 1
fi

# Count current workers
echo "📊 Counting current workers..."
WORKER_COUNT=$(screen -ls 2>/dev/null | grep -c repworker || echo "0")
echo "   Found: $WORKER_COUNT workers"

if [ "$WORKER_COUNT" -eq 0 ]; then
    echo "⚠️  No workers found. Starting fresh..."
    python restart_workers_fast.py "$@"
else
    echo "🔄 Restarting $WORKER_COUNT workers..."
    
    if [ "$1" = "--method=bash" ]; then
        echo "   Using: Bash kill + Python start"
        ./kill_workers_fast.sh
        python restart_workers.py "${@:2}"
    elif [ "$1" = "--method=original" ]; then
        echo "   Using: Original method (slow)"
        python restart_workers.py "${@:2}"
    else
        echo "   Using: Optimized Python (recommended)"
        python restart_workers_fast.py "$@"
    fi
fi

# Count final workers
echo "📊 Final worker count..."
sleep 2
FINAL_COUNT=$(screen -ls 2>/dev/null | grep -c repworker || echo "0")
echo "   Result: $FINAL_COUNT workers"

if [ "$FINAL_COUNT" -gt 0 ]; then
    echo "✅ Success! Workers restarted."
else
    echo "❌ Warning: No workers running after restart."
fi

echo ""
echo "Usage examples:"
echo "  ./restart_workers_quick.sh                    # Fast restart (recommended)"
echo "  ./restart_workers_quick.sh --clear-queues     # Fast restart + clear queues"
echo "  ./restart_workers_quick.sh --method=bash      # Bash kill + normal start"
echo "  ./restart_workers_quick.sh --method=original  # Original slow method" 