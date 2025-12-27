import argparse
import sys
import threading
import queue
from pathlib import Path

try:
    from src.watcher import VibeWatcher, Observer, process_queue
    from src.scanner import ProjectScanner
    from src.pruner import Pruner
    from src.monitor import Monitor
    from src.ignore_manager import IgnoreFileManager
    from src.core import console, logger
    from src.config import Config, VERSION
except ImportError as e:
    print(f"Error: {e}. Run from project root.", file=sys.stderr)
    sys.exit(1)

def install_hook(root: Path):
    Config.init(root)
    hooks = root / ".git" / "hooks"
    if not hooks.exists():
        console.print("[red]Not a git repo.[/red]")
        return
    
    hook = hooks / "pre-commit"
    python_exec = sys.executable
    script_path = root / "main.py"
    
    script_content = f"""#!/bin/sh
# Ghost Protocol Pre-Commit Hook
"{python_exec}" "{script_path}" --commit-check
"""
    hook.write_text(script_content, encoding="utf-8")
    hook.chmod(0o755)
    console.print("[green]✅ Hook Installed[/green]")

def run_commit_check(root: Path):
    try:
        Config.init(root)
        Pruner(root).cleanup()
        scanner = ProjectScanner(root)
        if not scanner.scan_staged():
            sys.exit(1)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Commit check failed: {e}")
        sys.exit(1)

def run_ghost_mode(root: Path):
    console.print(f"[bold cyan]👻 Ghost Protocol v{VERSION} Activated[/bold cyan]")
    Config.init(root)
    
    ignore_mgr = IgnoreFileManager(root)
    task_queue = queue.Queue(maxsize=5000)
    shutdown_event = threading.Event()
    
    worker_thread = threading.Thread(
        target=process_queue, 
        args=(root, task_queue, shutdown_event, ignore_mgr), 
        daemon=True
    )
    worker_thread.start()
    
    # VibeWatcher now takes only root and queue
    event_handler = VibeWatcher(root, task_queue)
    observer = Observer()
    observer.schedule(event_handler, str(root), recursive=True)
    observer.start()

    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        logger.info("[Ghost] Shutting down...")
        shutdown_event.set()
        observer.stop()
    observer.join()
    console.print("[yellow]Ghost stopped.[/yellow]")

def run_monitor(root: Path):
    Config.init(root)
    Monitor(root).start()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="Install git hook")
    parser.add_argument("--ghost", action="store_true", help="Run background watcher")
    parser.add_argument("--monitor", action="store_true", help="Show stats dashboard")
    parser.add_argument("--commit-check", action="store_true", help="Internal: Git hook")
    args = parser.parse_args()
    root = Path.cwd()

    if args.install:
        install_hook(root)
    elif args.ghost:
        run_ghost_mode(root)
    elif args.monitor:
        run_monitor(root)
    elif args.commit_check:
        run_commit_check(root)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()