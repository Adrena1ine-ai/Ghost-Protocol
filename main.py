import argparse
import sys
import threading
import queue
import subprocess
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
        Pruner(root).cleanup()
        scanner = ProjectScanner(root)
        if not scanner.scan_staged():
            sys.exit(1)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Commit check failed: {e}")
        sys.exit(1)

def run_full_start(root: Path):
    console.print(f"[bold cyan]👻 Ghost Protocol v{VERSION} Activated[/bold cyan]")
    
    # 1. Init Config & Environment (Trash folder, ignores)
    Config.init(root)
    
    # 2. Auto-install dependencies (Ruff, Radon, etc.)
    if Config.get().auto_install_deps:
        deps = ["ruff", "radon", "google-genai", "pyperclip"]
        for dep in deps:
            try:
                __import__(dep)
            except ImportError:
                logger.info(f"[Setup] Installing missing dependency: {dep}...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", dep], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logger.info(f"[Setup] {dep} installed successfully.")
                except subprocess.CalledProcessError:
                    logger.error(f"[Setup] Failed to install {dep}. Some features may not work.")

    # 3. Ignore Manager (Creates .cursorignore, .gitignore, _trash)
    ignore_mgr = IgnoreFileManager(root)

    # 4. Initial Scan (Stats & Token Count)
    scanner = ProjectScanner(root)
    scanner.scan_full_project()

    # 5. Watcher Thread (Background File System)
    task_queue = queue.Queue(maxsize=5000)
    shutdown_event = threading.Event()
    
    worker_thread = threading.Thread(
        target=process_queue, 
        args=(root, task_queue, shutdown_event, ignore_mgr), 
        daemon=True
    )
    worker_thread.start()
    
    # 6. UI Thread (Monitor - Frontend)
    # Monitor теперь сам запускает watcher
    monitor = Monitor(root, worker_thread, task_queue, shutdown_event, ignore_mgr, scanner)
    monitor.start()

def main():
    parser = argparse.ArgumentParser(description="Ghost Protocol - Automated guardian of your sanity")
    parser.add_argument("--install", action="store_true", help="Install git hook")
    parser.add_argument("--commit-check", action="store_true", help="Internal: Git hook")
    args = parser.parse_args()
    root = Path.cwd()

    if args.install:
        install_hook(root)
    elif args.commit_check:
        run_commit_check(root)
    else:
        # Если нет флагов -> Полный старт (Watcher + Monitor)
        run_full_start(root)

if __name__ == "__main__":
    main()
