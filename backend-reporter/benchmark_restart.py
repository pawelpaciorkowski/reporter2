#!/usr/bin/env python3
"""
Benchmark script to compare restart times
"""

import time
import subprocess
import sys

def time_command(cmd, description):
    """Time a command execution"""
    print(f"\n=== {description} ===")
    print(f"Command: {' '.join(cmd)}")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Duration: {duration:.2f} seconds")
        print(f"Exit code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:", result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
            
        return duration, result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Command timed out after 5 minutes!")
        return 300, False
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"Command failed after {duration:.2f} seconds: {e}")
        return duration, False


def count_workers():
    """Count current number of workers"""
    try:
        result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        count = result.stdout.count('repworker-')
        return count
    except:
        return 0


if __name__ == '__main__':
    print("Worker Restart Benchmark")
    print("=" * 50)
    
    # Count initial workers
    initial_workers = count_workers()
    print(f"Initial worker count: {initial_workers}")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test-old':
        # Test original version
        print("\nTesting ORIGINAL restart_workers.py...")
        duration, success = time_command(['python', 'restart_workers.py'], 
                                       "Original restart_workers.py")
    else:
        # Test new version by default
        print("\nTesting OPTIMIZED restart_workers_fast.py...")
        duration, success = time_command(['python', 'restart_workers_fast.py'], 
                                       "Optimized restart_workers_fast.py")
    
    # Count final workers
    final_workers = count_workers()
    print(f"\nFinal worker count: {final_workers}")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Total time: {duration:.2f} seconds")
    print(f"Success: {success}")
    print(f"Workers: {initial_workers} → {final_workers}")
    
    if success and initial_workers > 0:
        workers_per_second = initial_workers / duration if duration > 0 else 0
        print(f"Performance: {workers_per_second:.1f} workers/second")
    
    print("\nTo compare:")
    print("  python benchmark_restart.py           # Test fast version")
    print("  python benchmark_restart.py --test-old # Test original version") 