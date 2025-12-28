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

def ensure_dependencies():
    """Автоматическая установка недостающих зависимостей"""
    deps = ["ruff", "radon", "pyperclip", "google-genai"]
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            logger.info(f"[Setup] Installing missing dependency: {dep}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep], stdout=subprocess.DEVNULL)
                logger.info(f"[Setup] {dep} installed successfully.")
            except subprocess.CalledProcessError:
                logger.error(f"[Setup] Failed to install {dep}. Some features may not work.")

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
    
    # Установка зависимостей
    if Config.get().auto_install_deps:
        ensure_dependencies()
    
    ignore_mgr = IgnoreFileManager(root)
    task_queue = queue.Queue(maxsize=5000)
    shutdown_event = threading.Event()
    
    worker_thread = threading.Thread(
        target=process_queue, 
        args=(root, task_queue, shutdown_event, ignore_mgr), 
        daemon=True
    )
    worker_thread.start()
    
    event_handler = VibeWatcher(root, task_queue)
    observer = Observer()
    observer.schedule(event_handler, str(root), recursive=True)
    observer.start()

    if not observer.is_alive():
        logger.error("[Ghost] Observer failed to start.")
        console.print("[red]❌ Ghost failed to start.[/red]")
        return

    logger.info("[Ghost] Watching for file changes...")
    console.print("[green]✅ Ghost is now watching your project[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

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
    if Config.get().auto_install_deps:
        ensure_dependencies()
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