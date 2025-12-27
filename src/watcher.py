import time
import threading
import queue
from pathlib import Path
from typing import Dict, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .config import Config
from .core import logger

class VibeWatcher(FileSystemEventHandler):
    def __init__(self, root: Path, task_queue: queue.Queue):
        self.root = root
        self.task_queue = task_queue
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
    # ignore_mgr passed here for usage in batch_add_to_ignore logic
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
            assets_to_ignore = set()
            cfg = Config.get()
            
            for f_str in ready_files:
                path = Path(f_str)
                if not path.exists(): continue
                
                try:
                    size_mb = path.stat().st_size / (1024 * 1024)
                    ext = get_extension(path)

                    if size_mb > cfg.max_asset_size_mb:
                        if ext in cfg.garbage_extensions:
                            rel_path = str(path.relative_to(root)).replace("\\", "/")
                            assets_to_ignore.add(rel_path)
                            continue

                    if size_mb > cfg.max_code_size_mb and ext in cfg.code_extensions:
                        logger.warning(f"[WARN] Heavy code: {path.name} ({size_mb:.2f} MB)")
                except OSError: pass
            
            if assets_to_ignore: 
                ignore_mgr.add_entries(assets_to_ignore)