import fnmatch
from pathlib import Path
from typing import List, Set
from .config import Config
from .core import logger
from .utils import interprocess_lock, atomic_write

class IgnoreFileManager:
    """Centralized manager for .gitignore and .cursorignore operations."""
    
    def __init__(self, root: Path):
        self.root = root
        self.cfg = Config.get()
        self.targets = [
            self.root / self.cfg.gitignore_file, 
            self.root / self.cfg.cursorignore_file
        ]
    
    def ensure_files_exist(self):
        """Create ignore files and fill with default rules if empty."""
        default_rules = [
            "# Ghost Protocol auto-generated rules",
            "",
            "# Directories",
            "venv/",
            ".venv/",
            "env/",
            "__pycache__/",
            "node_modules/",
            ".git/",
            "_trash/",
            "",
            "# Files",
            "*.pyc",
            "*.pyo",
            ".DS_Store",
            "*.log",
            "",
            "# SECURITY: Never commit API keys!",
            "ghost_config.json",
            ".ghost_config.json",
            "*.api_key",
            ".env",
            ".env.local",
            ""
        ]
        
        for target in self.targets:
            target.touch(exist_ok=True)
            
            # Если файл пустой - заполняем базовыми правилами
            content = target.read_text(encoding="utf-8")
            if not content.strip():
                new_content = "\n".join(default_rules)
                atomic_write(target, new_content)
                logger.info(f"[Ghost] Initialized {target.name} with default rules")

    def add_entries(self, paths_to_add: Set[str], targets: List[Path] = None):
        """
        Добавляет пути в файлы игнора.
        
        Args:
            paths_to_add: Пути для добавления
            targets: Список файлов куда писать. 
                     None = оба файла (.gitignore + .cursorignore)
                     [gitignore] = только .gitignore (для DATA файлов)
        
        Returns:
            Количество добавленных записей
        """
        if not paths_to_add: 
            return 0
        
        # Если targets не указаны — пишем в оба файла (JUNK)
        if targets is None:
            targets = self.targets  # [.gitignore, .cursorignore]
        
        total_added = 0
        
        for target in targets:
            added = self._add_to_file(target, paths_to_add)
            total_added += added
        
        if total_added > 0:
            target_names = [t.name for t in targets]
            logger.info(f"[Ghost] Added {len(paths_to_add)} entries to {', '.join(target_names)}")
        
        return total_added
    
    def add_junk(self, paths: Set[str]) -> int:
        """Добавляет JUNK файлы в ОБА игнора (.gitignore + .cursorignore)"""
        return self.add_entries(paths, targets=None)
    
    def add_data(self, paths: Set[str]) -> int:
        """Добавляет DATA файлы ТОЛЬКО в .gitignore (AI продолжает видеть)"""
        gitignore = self.root / self.cfg.gitignore_file
        result = self.add_entries(paths, targets=[gitignore])
        if result > 0:
            logger.info(f"[Ghost] DATA files added to .gitignore only - AI can still see them")
        return result

    def _add_to_file(self, target: Path, paths: Set[str]) -> int:
        """Helper: добавляет пути в конкретный файл"""
        target.touch(exist_ok=True)
        added_count = 0
        
        with interprocess_lock(target):
            content = target.read_text(encoding="utf-8")
            current_lines = set(content.splitlines())
            
            new_entries = []
            for p in paths:
                ghost_line = f"{p}  {self.cfg.ghost_tag}"
                if ghost_line not in current_lines and p not in current_lines:
                    new_entries.append(ghost_line)
                    added_count += 1

            if new_entries:
                if content and not content.endswith('\n'): content += '\n'
                content += "\n".join(new_entries) + "\n"
                atomic_write(target, content)
        
        return added_count

    def prune_stale(self):
        """Remove ghost-tagged lines for files that no longer exist."""
        for target in self.targets:
            self._prune_file(target)

    def _prune_file(self, target: Path):
        if not target.exists(): return
        
        try:
            with interprocess_lock(target):
                content = target.read_text(encoding="utf-8")
                lines = content.splitlines()
                new_lines: List[str] = []
                removed_count = 0

                for line in lines:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        new_lines.append(line)
                        continue
                    
                    if stripped.endswith(self.cfg.ghost_tag):
                        original_path = stripped.replace(self.cfg.ghost_tag, "").strip()
                        if (self.root / original_path).exists():
                            new_lines.append(line)
                        else:
                            removed_count += 1
                    else:
                        new_lines.append(line)

                if removed_count > 0:
                    new_content = "\n".join(new_lines)
                    if not new_content.endswith('\n'): new_content += '\n'
                    atomic_write(target, new_content)
                    logger.info(f"[Ghost] Pruned {removed_count} rules from {target.name}")
        except Exception as e:
            logger.error(f"Prune error: {e}")
            raise

    def is_ignored(self, rel_path: str, cursor_only: bool = False) -> bool:
        """
        Проверяет, игнорируется ли файл.
        
        Args:
            rel_path: Относительный путь к файлу
            cursor_only: Если True, проверяет только .cursorignore (для подсчета токенов)
        
        Returns:
            True если файл в игноре
        """
        # 1. Проверяем junk_file_patterns из конфига (FULL_PROJECT_CODE.txt и т.д.)
        file_name = Path(rel_path).name
        for pattern in self.cfg.junk_file_patterns:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                return True
        
        # 2. Проверяем размер файла - большие .txt файлы считаем мусором (конфигурируемо)
        try:
            file_path = self.root / rel_path
            if file_path.exists() and file_path.suffix.lower() == '.txt':
                size_kb = file_path.stat().st_size / 1024
                txt_limit = self.cfg.txt_max_size_kb
                if size_kb > txt_limit:
                    return True
        except OSError:
            pass
        
        # 3. Нормализуем путь (убираем начальный /, заменяем \ на /)
        normalized = rel_path.replace("\\", "/").lstrip("/")
        
        # 4. Определяем какие файлы проверять
        if cursor_only:
            targets_to_check = [self.root / self.cfg.cursorignore_file]
        else:
            targets_to_check = self.targets
        
        # 5. Проверяем каждый файл игнора
        for target in targets_to_check:
            if not target.exists():
                continue
            try:
                with interprocess_lock(target):
                    content = target.read_text(encoding="utf-8")
                    lines = content.splitlines()
                    
                    for line in lines:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        
                        # Убираем ghost_tag если есть
                        if stripped.endswith(self.cfg.ghost_tag):
                            ignore_pattern = stripped.replace(self.cfg.ghost_tag, "").strip()
                        else:
                            ignore_pattern = stripped
                        
                        # Точное совпадение
                        if normalized == ignore_pattern or normalized.endswith("/" + ignore_pattern):
                            return True
                        
                        # Проверка паттернов с *
                        if "*" in ignore_pattern:
                            if fnmatch.fnmatch(normalized, ignore_pattern):
                                return True
                            if fnmatch.fnmatch(file_name, ignore_pattern):
                                return True
                        
                        # Проверка директорий (если паттерн заканчивается на /)
                        if ignore_pattern.endswith("/"):
                            if normalized.startswith(ignore_pattern.rstrip("/")):
                                return True
            except Exception as e:
                logger.debug(f"Error checking ignore file {target.name}: {e}")
                continue
        
        return False