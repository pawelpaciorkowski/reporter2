#!/usr/bin/env python3
"""
Fast parallel worker starter - only starts workers without killing existing ones
"""

import subprocess
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config
from api.common import get_db
from helpers import divide_chunks

cfg = Config()

SAMODZIELNE_WORKERY = ['ZAWODZI', 'CZERNIA', 'RZESZOW', 'PRZ-PLO', 'LODZ', 'BYDGOW', 'SIEDLCE', 'LUBLIN', 'LUBLINC']


def execute_with_timeout(cmd, timeout=10):
    """Execute command with timeout"""
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate(timeout=timeout)
        return out.decode(), proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return "", -1


def clear_queue_if_needed(queue):
    if '--clear-queues' not in sys.argv:
        return
    cmd = [cfg.RQ_EXECUTABLE, 'empty', queue]
    execute_with_timeout(cmd, 10)


def start_screen(name, command):
    cmd = ['screen', '-dm', '-S', name]
    if isinstance(command, list):
        for scmd in command:
            cmd.append(scmd)
    else:
        cmd.append(command)
    print('starting screen', name, command)
    execute_with_timeout(cmd, 10)


def start_worker_screen_safe(queue):
    """Thread-safe worker screen starter"""
    try:
        clear_queue_if_needed(queue)
        screen_name = queue.replace('execute/', '').replace('/', '_')
        screen_name = 'repworker-' + screen_name
        screen_name += str(int(time.time() % 100000 ))
        cmd = [cfg.RQ_EXECUTABLE, 'worker', '--with-scheduler', queue]
        cmd += ['-n', screen_name]
        if cfg.SENTRY_URL is not None:
            cmd += ['--sentry-dsn', cfg.SENTRY_URL]
        start_screen(screen_name, cmd)
        return True
    except Exception as e:
        print(f'Failed to start worker for {queue}: {e}')
        return False


def start_multiworker_screen_safe(type, prio, targets):
    """Thread-safe multiworker screen starter"""
    try:
        screen_name = 'repworker-multi-%s_%d_%s' % (type, prio, targets[0])
        screen_name += str(int(time.time() % 100000 ))
        queues = ['execute/%s/%d/%s' % (type, prio, target) for target in targets]
        for queue in queues:
            clear_queue_if_needed(queue)
        cmd = [cfg.RQ_EXECUTABLE, 'worker', '--with-scheduler']
        cmd += ['-n', screen_name]
        if cfg.SENTRY_URL is not None:
            cmd += ['--sentry-dsn', cfg.SENTRY_URL]
        cmd += queues
        start_screen(screen_name, cmd)
        return True
    except Exception as e:
        print(f'Failed to start multiworker {type}/{prio}/{targets}: {e}')
        return False


def start_all_workers_parallel():
    """Start all workers in parallel"""
    print("Starting all workers in parallel...")
    
    # Prepare all worker tasks
    worker_tasks = []
    
    # Get laboratories and prepare multiworker tasks
    centrumy = []
    with get_db() as db:
        for row in db.select('select * from laboratoria'):
            if row['adres'] is not None:
                if row['symbol'] in SAMODZIELNE_WORKERY:
                    # Independent workers
                    worker_tasks.append(('multi', 'centrum', 0, [row['symbol']]))
                    worker_tasks.append(('multi', 'centrum', 1, [row['symbol']]))
                else:
                    centrumy.append(row['symbol'])
    
    # Group regular laboratories
    for chunk in divide_chunks(centrumy, 4):
        if 'KOPERNI' in chunk:
            chunk.append('KOPERNIKA')
        worker_tasks.append(('multi', 'centrum', 0, chunk))
        worker_tasks.append(('multi', 'centrum', 1, chunk))
    
    # Add other workers
    other_workers = [
        'execute/snr/0', 'execute/snr/1',
        'execute/ick/0', 'execute/ick/1', 'execute/ick/2'
    ]
    for queue in other_workers:
        worker_tasks.append(('single', queue))
    
    print(f"Starting {len(worker_tasks)} workers...")
    
    # Start all workers in parallel
    with ThreadPoolExecutor(max_workers=min(30, len(worker_tasks))) as executor:
        futures = []
        
        for task in worker_tasks:
            if task[0] == 'multi':
                _, type, prio, targets = task
                future = executor.submit(start_multiworker_screen_safe, type, prio, targets)
            else:  # single
                _, queue = task
                future = executor.submit(start_worker_screen_safe, queue)
            futures.append(future)
        
        # Wait for completion with progress
        completed = 0
        for future in as_completed(futures, timeout=60):
            try:
                success = future.result()
                completed += 1
                if completed % 10 == 0:
                    print(f'Started {completed}/{len(worker_tasks)} workers')
            except Exception as exc:
                print(f'Worker start failed: {exc}')
                completed += 1
    
    print(f"All {len(worker_tasks)} workers started!")


if __name__ == '__main__':
    print("Fast worker starter - parallel version")
    print("This will start workers without killing existing ones")
    
    start_all_workers_parallel()
    
    print("Worker startup completed!") 