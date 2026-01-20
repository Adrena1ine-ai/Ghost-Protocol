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
from .classifier import FileClassifier
from .analyzer import CodeAnalyzer

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

def process_queue(root: Path, task_queue: queue.Queue, shutdown_event: threading.Event, ignore_mgr, event_callback=None, ai_reviewer=None):
    """
    Воркер-поток: обрабатывает очередь файловых событий.
    Использует FileClassifier для умной классификации.
    
    God Mode: Для CODE файлов автоматически запускает Ruff и AI Review.
    """
    pending_files: Dict[str, float] = {} 
    MAX_PENDING = 1000
    classifier = FileClassifier(root)
    analyzer = CodeAnalyzer(root)
    
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
            junk_to_ignore = set()  # JUNK -> оба файла
            data_to_ignore = set()  # DATA -> только .gitignore
            
            for f_str in ready_files:
                path = Path(f_str)
                if not path.exists(): continue
                
                try:
                    rel_path = str(path.relative_to(root)).replace("\\", "/")
                    
                    # Используем умный классификатор
                    action = classifier.classify(path)
                    
                    if action == "CODE" or action == "CRITICAL":
                        # God Mode: Проверяем код через Ruff и AI
                        # 1. Проверяем Ruff (мгновенное исправление)
                        success, error_msg, diff = analyzer.check_file(path)
                        if success is False and diff:
                            # Ruff нашёл ошибки - создаём Auto-Fix задачу
                            from .task_manager import TaskManager
                            task_mgr = TaskManager(root)
                            task_mgr.write_task(
                                task_type="Auto-Fix",
                                file_path=rel_path,
                                diff=diff,
                                instruction="Apply this diff automatically.",
                                reason=f"Ruff lint errors: {error_msg[:100]}"
                            )
                            logger.info(f"[Ghost] Auto-Fix generated for {path.name}. Waiting for Cursor...")
                            if event_callback:
                                event_callback(f"Auto-Fix task: {path.name}")
                        
                        # 2. Если Ruff чист и изменения > 50 строк, отправляем в AI
                        if ai_reviewer and success is not False:
                            diff_lines = analyzer.get_file_diff_lines(path)
                            if diff_lines > 50:
                                # Вызываем AI Review в авторежиме
                                ai_reviewer.run_review(file_path=path, auto_mode=True)
                                if event_callback:
                                    event_callback(f"AI review triggered: {path.name}")
                        
                        continue
                    
                    elif action == "TRASH":
                        # Перемещаем в корзину
                        rel = move_to_trash(root, path, cfg.trash_folder)
                        logger.info(f"[Ghost] Auto-moved to trash: {rel}")
                        trash_count += 1
                        if event_callback:
                            event_callback(f"Moved to trash: {path.name}")
                    
                    elif action == "JUNK":
                        # Добавляем в оба файла (.gitignore + .cursorignore)
                        junk_to_ignore.add(rel_path)
                        logger.info(f"[Ghost] Classified as JUNK: {path.name}")
                    
                    elif action == "DATA":
                        # Добавляем только в .gitignore (ИИ должен видеть)
                        data_to_ignore.add(rel_path)
                        logger.info(f"[Ghost] Classified as DATA: {path.name}")
                    
                    # UNKNOWN — оставляем как есть
                    
                except OSError: pass
            
            # Батч-добавление в игнор (используем явные методы)
            junk_count = 0
            data_count = 0
            
            if junk_to_ignore:
                junk_count = ignore_mgr.add_junk(junk_to_ignore)
            
            if data_to_ignore:
                data_count = ignore_mgr.add_data(data_to_ignore)
            
            if junk_count > 0 or data_count > 0:
                if event_callback:
                    if junk_count > 0 and data_count > 0:
                        event_callback(f"Ignored: {len(junk_to_ignore)} junk, {len(data_to_ignore)} data")
                    elif junk_count > 0:
                        event_callback(f"Ignored: {len(junk_to_ignore)} junk files")
                    elif data_count > 0:
                        event_callback(f"Ignored: {len(data_to_ignore)} data files (AI sees)")
            
            if trash_count > 0:
                if event_callback:
                    event_callback(f"Moved {trash_count} files to _trash")