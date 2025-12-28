import argparse
import sys
import threading
import queue
import subprocess
import os
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
    console.print("[green][OK] Hook Installed[/green]")

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
    console.print(f"[bold cyan]Ghost Protocol v{VERSION} Activated[/bold cyan]")
    
    # 1. Init Config & Environment (Trash folder, ignores)
    Config.init(root)
    
    # 2. Auto-install dependencies (Ruff, Radon, etc.)
    if Config.get().auto_install_deps:
        deps = ["ruff", "radon", "google-generativeai", "pyperclip"]
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

    # 3. Create _trash folder
    trash_folder = root / Config.get().trash_folder
    trash_folder.mkdir(exist_ok=True)
    console.print(f"[green][OK][/green] Created/verified trash folder: [cyan]{Config.get().trash_folder}[/cyan]")
    logger.info(f"[Ghost] Created/verified trash folder: {Config.get().trash_folder}")

    # 4. Ignore Manager (Creates .cursorignore, .gitignore)
    ignore_mgr = IgnoreFileManager(root)
    ignore_mgr.ensure_files_exist()
    console.print(f"[green][OK][/green] Created/verified ignore files: [cyan].gitignore[/cyan], [cyan].cursorignore[/cyan]")
    logger.info(f"[Ghost] Created/verified ignore files: .gitignore, .cursorignore")

    # 5. Initial Scan (Stats & Token Count)
    console.print("[yellow][*] Scanning project...[/yellow]")
    scanner = ProjectScanner(root, ignore_mgr)  # Передаем ignore_mgr для фильтрации Top 10
    scanner.scan_full_project()
    stats = scanner.get_stats()
    console.print(f"[green][OK] Project scan completed: {stats.get('files_count', 0)} files, {stats.get('total_tokens', 0):,} tokens[/green]")
    
    # 5.1. Initial scan for existing files (using FileClassifier)
    console.print("[yellow][*] Classifying existing files...[/yellow]")
    from src.utils import move_to_trash
    from src.classifier import FileClassifier
    
    cfg = Config.get()
    classifier = FileClassifier(root)
    junk_found = set()
    data_found = set()
    trash_count = 0
    
    try:
        for root_dir, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in cfg.skip_dirs and not d.startswith(".")]
            for file in files:
                file_path = Path(root_dir) / file
                if file.startswith(".ghost"): continue
                
                try:
                    # Используем умный классификатор
                    action = classifier.classify(file_path)
                    rel_path = str(file_path.relative_to(root)).replace("\\", "/")
                    
                    if action == "TRASH":
                        move_to_trash(root, file_path, cfg.trash_folder)
                        trash_count += 1
                    elif action == "JUNK":
                        junk_found.add(rel_path)
                    elif action == "DATA":
                        data_found.add(rel_path)
                    # CODE, CRITICAL, UNKNOWN — не трогаем
                except OSError:
                    continue
        
        # Добавляем в игнор (используем явные методы)
        if junk_found:
            ignore_mgr.add_junk(junk_found)
        if data_found:
            ignore_mgr.add_data(data_found)
        
        if junk_found or data_found:
            console.print(f"[green][OK] Classified: {len(junk_found)} junk, {len(data_found)} data files[/green]")
            logger.info(f"[Ghost] Initial scan: {len(junk_found)} junk, {len(data_found)} data files")
        
        if trash_count > 0:
            console.print(f"[green][OK] Moved {trash_count} files to _trash[/green]")
            logger.info(f"[Ghost] Initial scan: moved {trash_count} files to trash")
    except Exception as e:
        logger.debug(f"Initial classification error (non-critical): {e}")

    # 6. Watcher Thread (Background File System)
    task_queue = queue.Queue(maxsize=5000)
    shutdown_event = threading.Event()
    
    # 7. UI Thread (создаем monitor сначала, чтобы передать callback)
    monitor = Monitor(root, scanner, task_queue, shutdown_event, ignore_mgr)
    
    # 8. Watcher Thread (передаем callback для событий)
    worker_thread = threading.Thread(
        target=process_queue, 
        args=(root, task_queue, shutdown_event, ignore_mgr, monitor.add_log), 
        daemon=True
    )
    worker_thread.start()
    console.print("[green][OK] Background watcher thread started[/green]")
    logger.info("[Ghost] Background watcher thread started")
    
    # 9. Запускаем Monitor
    monitor.start()

def run_setup():
    """Запускает интерактивный мастер настройки"""
    try:
        from src.global_config import run_setup_wizard
        run_setup_wizard()
    except ImportError as e:
        console.print(f"[red]Setup error: {e}[/red]")
        sys.exit(1)

def show_config_info():
    """Показывает информацию о текущей конфигурации"""
    try:
        from src.global_config import GlobalConfig
        cfg = GlobalConfig.get()
        console.print("\n[bold cyan]Ghost Protocol Configuration[/bold cyan]")
        console.print(f"  Config location: [dim]{cfg.config_location}[/dim]")
        console.print(f"  Provider: [green]{cfg.provider}[/green]")
        console.print(f"  Model: [green]{cfg.model}[/green]")
        if cfg.api_key:
            masked_key = cfg.api_key[:8] + "..." + cfg.api_key[-4:] if len(cfg.api_key) > 12 else "***"
            console.print(f"  API Key: [dim]{masked_key}[/dim]")
        else:
            console.print("  API Key: [red]Not configured[/red]")
        console.print(f"  Setup complete: {'[green]Yes[/green]' if cfg.setup_complete else '[yellow]No[/yellow]'}")
    except Exception as e:
        console.print(f"[red]Error reading config: {e}[/red]")

def main():
    parser = argparse.ArgumentParser(description="Ghost Protocol - Automated guardian of your sanity")
    parser.add_argument("--install", action="store_true", help="Install git hook")
    parser.add_argument("--commit-check", action="store_true", help="Internal: Git hook")
    parser.add_argument("--setup", action="store_true", help="Configure AI provider and API key")
    parser.add_argument("--config", action="store_true", help="Show current configuration")
    args = parser.parse_args()
    root = Path.cwd()

    if args.setup:
        run_setup()
    elif args.config:
        show_config_info()
    elif args.install:
        install_hook(root)
    elif args.commit_check:
        run_commit_check(root)
    else:
        # Если нет флагов -> Полный старт (Watcher + Monitor)
        run_full_start(root)

if __name__ == "__main__":
    main()
