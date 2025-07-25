import subprocess
import time
import sys
import signal
import threading
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


def running_screens():
    res = []
    _ = execute_with_timeout(['screen', '-wipe'], 5)
    ls_res, _ = execute_with_timeout(['screen', '-wipe'], 5)
    for line in ls_res.split('\n'):
        if 'repworker-' in line:
            res.append(line.replace('\t', ' ').strip().split(' ')[0])
    return res


def kill_screen_safe(name):
    """Kill screen with timeout and fallback to force kill"""
    print(f'killing screen {name}')
    
    # Try graceful quit first
    out, code = execute_with_timeout(['screen', '-X', '-S', name, 'quit'], timeout=5)
    if code == 0:
        return True
        
    # If graceful quit failed, try to find and kill the process
    try:
        # Get screen PID
        result = subprocess.run(['screen', '-ls'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if name in line and 'repworker-' in line:
                # Extract PID from screen listing
                parts = line.strip().split()
                if parts and '.' in parts[0]:
                    pid = parts[0].split('.')[0]
                    try:
                        subprocess.run(['kill', '-9', pid], timeout=2)
                        print(f'Force killed PID {pid} for screen {name}')
                        return True
                    except:
                        pass
    except:
        pass
    
    return False


def kill_all_screens_parallel(screens):
    """Kill all screens in parallel"""
    if not screens:
        return
        
    print(f'Killing {len(screens)} workers in parallel...')
    
    with ThreadPoolExecutor(max_workers=min(20, len(screens))) as executor:
        # Submit all kill tasks
        future_to_screen = {executor.submit(kill_screen_safe, screen): screen 
                           for screen in screens}
        
        # Wait for completion
        completed = 0
        for future in as_completed(future_to_screen, timeout=30):
            screen = future_to_screen[future]
            try:
                success = future.result()
                completed += 1
                if completed % 10 == 0:
                    print(f'Completed {completed}/{len(screens)} kills')
            except Exception as exc:
                print(f'Screen {screen} generated an exception: {exc}')


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


def start_worker_screen(queue):
    clear_queue_if_needed(queue)
    screen_name = queue.replace('execute/', '').replace('/', '_')
    screen_name = 'repworker-' + screen_name
    screen_name += str(int(time.time() % 100000 ))
    cmd = [cfg.RQ_EXECUTABLE, 'worker', '--with-scheduler', queue]
    cmd += ['-n', screen_name]
    if cfg.SENTRY_URL is not None:
        cmd += ['--sentry-dsn', cfg.SENTRY_URL]
    start_screen(screen_name, cmd)


def start_multiworker_screen(type, prio, targets):
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


if __name__ == '__main__':
    print("Fast restart workers - optimized version")
    
    # Get all screens to kill
    screens = running_screens()
    print(f"Found {len(screens)} workers to restart")
    
    # Kill all screens in parallel
    if screens:
        kill_all_screens_parallel(screens)
        print("Waiting 3 seconds for cleanup...")
        time.sleep(3)
    
    # Start all workers in parallel
    start_all_workers_parallel()
    
    print("Workers restart completed!") 