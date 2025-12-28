import json
import subprocess
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
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
    def __init__(self, root: Path, ignore_mgr=None):
        self.root = root
        self.cfg = Config.get()
        self.cache_path = self.root / self.cfg.cache_file
        self.ignore_mgr = ignore_mgr  # Для фильтрации Top 10 Junk
        self._cached_folder_sizes: Dict[str, int] = {}  # Кэш размеров папок

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
            console.print("[bold red]COMMIT BLOCKED: Git timeout (30s).[/bold red]")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"[CRITICAL] Git failed: {e.stderr}")
            console.print("[bold red]COMMIT BLOCKED: Git status check failed.[/bold red]")
            return False
        except FileNotFoundError:
            logger.error("[CRITICAL] Git not found.")
            console.print("[bold red]COMMIT BLOCKED: Git not found.[/bold red]")
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
            console.print("[bold red]COMMIT BLOCKED: Giant source files detected![/bold red]")
            for v in code_violations: console.print(f"   - {v}")
            return False
        return True

    def scan_full_project(self, mode: str = 'smart'):
        """
        Сканирует проект и подсчитывает токены.
        
        Args:
            mode: 'smart' - быстрый скан (использует кэш), 'deep' - полный скан
        """
        total_bytes = 0
        saved_bytes = 0  # Токены игнорированных файлов
        file_count = 0
        top_files = [] # Список кортежей (path, tokens)
        
        cfg = Config.get()
        skip_dirs_set = set(cfg.skip_dirs)
        
        try:
            for root_dir, dirs, files in os.walk(self.root):
                # Фильтруем директории
                dirs[:] = [d for d in dirs if d not in skip_dirs_set and not d.startswith(".")]
                
                # Если папка в skip_dirs, проверяем кэш (для mode='smart')
                current_dir = Path(root_dir)
                if mode == 'smart' and current_dir.name in skip_dirs_set:
                    rel_dir = str(current_dir.relative_to(self.root))
                    if rel_dir in self._cached_folder_sizes:
                        saved_bytes += self._cached_folder_sizes[rel_dir]
                        continue  # Пропускаем сканирование этой папки
                
                for file in files:
                    file_path = Path(root_dir) / file
                    if file.startswith(".ghost"): continue
                    
                    try:
                        rel_path_str = str(file_path.relative_to(self.root))
                        
                        # Фильтр: читаем только текстовые файлы
                        if file_path.suffix.lower() in SAFE_TEXT_EXTENSIONS:
                            # Обработка UnicodeDecodeError для бинарников
                            try:
                                # Попытка прочитать как текст для проверки
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    f.read(1)  # Читаем первый байт для проверки
                            except UnicodeDecodeError:
                                # Файл бинарный, пропускаем
                                continue
                            except OSError:
                                continue
                            
                            size_bytes = file_path.stat().st_size
                            tokens = size_bytes // cfg.bytes_per_token
                            
                            # Проверяем, не игнорируется ли файл
                            is_ignored = False
                            if self.ignore_mgr:
                                try:
                                    is_ignored = self.ignore_mgr.is_ignored(rel_path_str, cursor_only=True)
                                except Exception as e:
                                    logger.debug(f"Error checking is_ignored for {rel_path_str}: {e}")
                            
                            if is_ignored:
                                # Считаем в saved_bytes (токены в игноре)
                                saved_bytes += size_bytes
                            else:
                                # Считаем в total_bytes (активные токены)
                                total_bytes += size_bytes
                                file_count += 1
                                top_files.append((file_path, tokens))  # Сохраняем токены, а не байты
                    except OSError: continue

            # Сортируем по токенам (обратно), берем топ 10
            top_files.sort(key=lambda x: x[1], reverse=True)
            
            # Фильтруем Top 10: исключаем файлы, уже в игноре (только неигнорированные файлы)
            # Примечание: файлы уже отфильтрованы по .cursorignore на этапе подсчета токенов,
            # но здесь проверяем еще раз для безопасности (на случай если ignore_mgr не был передан ранее)
            top_files_not_ignored = []
            if self.ignore_mgr:
                try:
                    for file_path, tokens in top_files:
                        rel_path = str(file_path.relative_to(self.root))
                        try:
                            if not self.ignore_mgr.is_ignored(rel_path, cursor_only=True):
                                top_files_not_ignored.append((file_path, tokens))
                            if len(top_files_not_ignored) >= 10:
                                break
                        except Exception as e:
                            logger.debug(f"Error checking if ignored {rel_path}: {e}")
                            # В случае ошибки включаем файл в топ
                            top_files_not_ignored.append((file_path, tokens))
                            if len(top_files_not_ignored) >= 10:
                                break
                    top_files = top_files_not_ignored[:10] if top_files_not_ignored else top_files[:10]
                except Exception as e:
                    logger.error(f"Error filtering top files: {e}")
                    top_files = top_files[:10]
            else:
                top_files = top_files[:10]

            # Сохраняем пути как строки для JSON (токены, не байты)
            top_files_serializable = [[str(p.relative_to(self.root)), int(tokens)] for p, tokens in top_files]

            stats: Dict[str, Any] = {
                "total_tokens": total_bytes // cfg.bytes_per_token,
                "saved_tokens": saved_bytes // cfg.bytes_per_token,  # Токены в игноре (включая trash)
                "files_count": file_count,
                "last_scan": time.time(),
                "top_files": top_files_serializable, # Сохраняем список тяжелых файлов [[path, tokens], ...]
                "cached_folder_sizes": self._cached_folder_sizes  # Кэш размеров папок
            }
            atomic_write(self.cache_path, json.dumps(stats, indent=2))
            logger.debug(f"Scan complete: {file_count} files, {len(top_files_serializable)} top files saved")
        except Exception as e:
            logger.error(f"Stats scan error: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        if self.cache_path.exists():
            try: 
                data = json.loads(self.cache_path.read_text())
                # Убеждаемся что все ключи есть (для старых кэшей)
                if 'top_files' not in data:
                    data['top_files'] = []
                if 'saved_tokens' not in data:
                    data['saved_tokens'] = 0
                if 'cached_folder_sizes' in data:
                    # Загружаем кэш размеров папок
                    self._cached_folder_sizes = data.get('cached_folder_sizes', {})
                return data
            except (IOError, json.JSONDecodeError) as e:
                logger.debug(f"Cache read error: {e}")
        return {"total_tokens": 0, "saved_tokens": 0, "files_count": 0, "last_scan": 0, "top_files": [], "cached_folder_sizes": {}}
