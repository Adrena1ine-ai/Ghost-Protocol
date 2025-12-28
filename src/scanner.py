import json
import subprocess
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from .config import Config
from .core import console, logger
from .utils import atomic_write

# Список расширений, которые мы "безопасно" читаем как текст
SAFE_TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", 
    ".java", ".c", ".cpp", ".rs", ".go", ".php", ".rb", ".md", ".txt", 
    ".yml", ".yaml", ".json", ".sql" # SQL нужен для дампа структуры
}

class ProjectScanner:
    def __init__(self, root: Path):
        self.root = root
        cfg = Config.get()
        self.cache_path = self.root / cfg.cache_file

    def scan_staged(self) -> bool:
        try:
            output = subprocess.check_output(
                ["git", "diff", "--cached", "--name-only", "-z"],
                cwd=self.root,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
        except subprocess.TimeoutExpired:
            logger.error("[CRITICAL] Git command timed out.")
            console.print("[bold red]⛔ COMMIT BLOCKED: Git timeout (30s).[/bold red]")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"[CRITICAL] Git failed: {e.stderr}")
            console.print("[bold red]⛔ COMMIT BLOCKED: Git status check failed.[/bold red]")
            return False
        except FileNotFoundError:
            logger.error("[CRITICAL] Git not found.")
            console.print("[bold red]⛔ COMMIT BLOCKED: Git not found.[/bold red]")
            return False

        if not output: return True
        
        staged_files = output.split('\x00')  # Исправлено: \x00 вместо \x0
        cfg = Config.get()
        code_violations: List[str] = []

        for f_str in staged_files:
            if not f_str: continue
            file_path = self.root / f_str
            try:
                suffix = file_path.suffix.lower()
                if suffix in cfg.code_extensions:
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if size_mb > cfg.max_code_size_mb:
                        code_violations.append(f"{f_str} ({size_mb:.2f} MB)")
            except OSError: continue

        if code_violations:
            console.print("[bold red]⛔ COMMIT BLOCKED: Giant source files detected![/bold red]")
            for v in code_violations: console.print(f"   - {v}")
            return False
        return True

    def scan_full_project(self) -> bool:
        total_bytes = 0
        file_count = 0
        cfg = Config.get()
        
        try:
            for root_dir, dirs, files in os.walk(self.root):
                dirs[:] = [d for d in dirs if d not in cfg.skip_dirs and not d.startswith(".")]
                for file in files:
                    file_path = Path(root_dir) / file
                    if file.startswith(".ghost"): continue
                    
                    try:
                        # ФИЛЬТР: Читаем только текстовые файлы (код, дампы, конфиги)
                        if file_path.suffix.lower() in SAFE_TEXT_EXTENSIONS:
                            total_bytes += file_path.stat().st_size
                            file_count += 1
                    except OSError: continue

            stats: Dict[str, Any] = {
                "total_tokens": total_bytes // cfg.bytes_per_token,
                "files_count": file_count,
                "last_scan": time.time()
            }
            atomic_write(self.cache_path, json.dumps(stats))
        except Exception as e:
            logger.debug(f"Stats scan error (non-critical): {e}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        if self.cache_path.exists():
            try: return json.loads(self.cache_path.read_text())
            except (IOError, json.JSONDecodeError): pass
        return {"total_tokens": 0, "files_count": 0, "last_scan": 0}
