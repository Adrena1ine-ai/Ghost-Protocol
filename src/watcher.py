import time
import threading
import queue
from pathlib import Path
from typing import Dict, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .config import Config
from .core import logger
from .utils import move_to_trash

class VibeWatcher(FileSystemEventHandler):
    def __init__(self, root: Path, task_queue: queue.Queue, ignore_mgr=None):
        self.root = root
        self.task_queue = task_queue
        self.ignore_mgr = ignore_mgr
        cfg = Config.get()
        self.ignore_files = {
            root / cfg.gitignore_file, 
            root / cfg.cursorignore_file
        }

    def _enqueue(self, path: Path):
        if path in self.ignore_files: return
        try:
            rel_path = path.relative_to(self.root)
        except ValueError:
            return
            
        cfg = Config.get()
        if any(part in cfg.skip_dirs for part in rel_path.parts): return
        if path.name.startswith("."): return
        
        self.task_queue.put(("check", path))

    def on_created(self, event):
        if not event.is_directory: self._enqueue(Path(event.src_path))
    def on_moved(self, event):
        if not event.is_directory: self._enqueue(Path(event.dest_path))
    def on_modified(self, event):
        if not event.is_directory: self._enqueue(Path(event.src_path))

def get_extension(path: Path) -> str:
    s = path.suffix.lower()
    if s == ".gz" and path.name.lower().endswith(".tar.gz"): return ".tar.gz"
    return s

def process_queue(root: Path, task_queue: queue.Queue, shutdown_event: threading.Event, ignore_mgr):
    pending_files: Dict[str, float] = {} 
    MAX_PENDING = 1000
    
    while not shutdown_event.is_set():
        try:
            cmd, path = task_queue.get(timeout=0.1)
            file_str = str(path)
            pending_files[file_str] = time.time()
            
            if len(pending_files) > MAX_PENDING:
                oldest = sorted(pending_files, key=pending_files.get)[:len(pending_files)//2]
                for k in oldest: del pending_files[k]
        except queue.Empty: pass
        
        now = time.time()
        ready_files: Set[str] = set()
        
        for f_str, timestamp in list(pending_files.items()):
            if now - timestamp > Config.get().debounce_seconds:
                ready_files.add(f_str)
                del pending_files[f_str]
        
        if ready_files:
            cfg = Config.get()
            trash_count = 0
            
            for f_str in ready_files:
                path = Path(f_str)
                if not path.exists(): continue
                
                try:
                    size_mb = path.stat().st_size / (1024 * 1024)
                    ext = get_extension(path)
                    name_lower = path.name.lower()

                    # --- ЛОГИКА КОРЗИНЫ (Auto-Cleanup) ---
                    # Признаки для автоматического переноса в _trash:
                    # 1. Очень большой файл ( > max_trash_size_mb )
                    # 2. Подозрительное название (dump, backup, copy, v2)
                    is_trash_candidate = (
                        size_mb > cfg.max_trash_size_mb or 
                        any(x in name_lower for x in ["dump", "backup", "copy", "old", "v2", "temp", "trash"])
                    )

                    # Исключаем критичные файлы проекта (main.py, config.py и т.д.)
                    # Простая эвристика: если файл в корне и имеет стандартное имя, не трогаем
                    is_critical = path.parent == root and name_lower in ["main.py", "config.py", "app.py", "manage.py"]

                    if is_trash_candidate and not is_critical:
                        rel = move_to_trash(root, path, cfg.trash_folder)
                        logger.info(f"[Ghost] Auto-moved to trash: {rel}")
                        trash_count += 1
                        continue # Не обрабатываем дальше

                    # --- СТАНДАРТНАЯ ЛОГИКА ИГНОРА ---
                    if size_mb > cfg.max_asset_size_mb:
                        if ext in cfg.garbage_extensions:
                            rel_path = str(path.relative_to(root)).replace("\\", "/")
                            ignore_mgr.add_entries({rel_path})
                            continue

                    if size_mb > cfg.max_code_size_mb and ext in cfg.code_extensions:
                        logger.warning(f"[WARN] Heavy code: {path.name} ({size_mb:.2f} MB)")
                except OSError: pass
            
            if trash_count > 0:
                logger.info(f"[Ghost] Cleaned up {trash_count} trash files.")