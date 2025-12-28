import os
import sys
import contextlib
import shutil
from pathlib import Path
from typing import Optional, IO

_FCNTL = None
_MSVCRT = None

if sys.platform != "win32":
    try:
        import fcntl as _fcntl_module
        _FCNTL = _fcntl_module
    except ImportError:
        pass
else:
    try:
        import msvcrt as _msvcrt_module
        _MSVCRT = _msvcrt_module
    except ImportError:
        pass

@contextlib.contextmanager
def interprocess_lock(target_file: Path):
    lock_path = target_file.with_name(f"{target_file.name}.lock")
    lock_fp: Optional[IO] = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        mode = 'a+b' if _MSVCRT else 'a+'
        lock_fp = open(lock_path, mode)
        if _FCNTL:
            _FCNTL.flock(lock_fp.fileno(), _FCNTL.LOCK_EX)
        elif _MSVCRT:
            _MSVCRT.locking(lock_fp.fileno(), _MSVCRT.LK_LOCK, 1)
        yield
    finally:
        if lock_fp:
            try:
                if _FCNTL:
                    _FCNTL.flock(lock_fp.fileno(), _FCNTL.LOCK_UN)
                elif _MSVCRT:
                    _MSVCRT.locking(lock_fp.fileno(), _MSVCRT.LK_UNLCK, 1)
                lock_fp.close()
            except Exception:
                pass

def atomic_write(path: Path, content: str):
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    os.replace(temp_path, path)

def move_to_trash(root: Path, file_path: Path, trash_folder_name: str = "_trash"):
    """
    Перемещает файл в корзину внутри проекта, сохраняя структуру папок.
    Например: root/data/dump.sql -> root/_trash/data/dump.sql
    """
    try:
        relative_path = file_path.relative_to(root)
        trash_dir = root / trash_folder_name
        
        # Определяем путь в корзине
        destination_dir = trash_dir / relative_path.parent
        destination_path = destination_dir / relative_path.name
        
        # Создаем папки
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        # Перемещаем
        shutil.move(str(file_path), str(destination_path))
        
        return relative_path # Возвращаем относительный путь для логов
    except Exception as e:
        raise Exception(f"Failed to move {file_path.name} to trash: {e}")