"""
FileClassifier — Умный классификатор файлов Ghost Protocol

Использует эвристики (Safe Zones) для мгновенной классификации 99% файлов.
Для сложных случаев может использовать AI.
"""

from pathlib import Path
from typing import Literal, Optional
from .config import Config
from .core import logger

# Типы классификации
FileAction = Literal["CODE", "CRITICAL", "JUNK", "DATA", "TRASH", "UNKNOWN"]


class FileClassifier:
    """
    Классификатор файлов по принципу Safe Zones.
    
    Зоны берутся из конфига (ghost_config.json):
    - code_folders: Папки с кодом (никогда не трогать)
    - junk_folders: Папки с мусором (всегда игнорировать)
    - critical_files: Критичные файлы в корне (защищены)
    """
    
    # Подозрительные слова в названии файла (захардкожены, редко меняются)
    SUSPICIOUS_WORDS = {
        "dump", "backup", "copy", "old", "v2", "temp", "trash",
        "test_data", "sample", "example", "mock", "fixture"
    }
    
    def __init__(self, root: Path):
        self.root = root
        self.cfg = Config.get()
        
        # Загружаем Safe Zones из конфига
        self.code_folders = self.cfg.code_folders
        self.junk_folders = self.cfg.junk_folders
        self.critical_files = self.cfg.critical_files
    
    def get_action(self, file_path: Path, size_mb: float = None) -> FileAction:
        """
        Алиас для classify() для совместимости со спецификацией.
        size_mb игнорируется, так как размер определяется внутри.
        """
        return self.classify(file_path)
    
    def classify(self, file_path: Path) -> FileAction:
        """
        Классифицирует файл и возвращает действие.
        
        Returns:
            - CODE: Код проекта, не трогать
            - CRITICAL: Критичный файл, защищён
            - JUNK: Мусор, добавить в оба игнора
            - DATA: Данные проекта, только .gitignore
            - TRASH: Переместить в _trash
            - UNKNOWN: Непонятно, оставить как есть
        """
        try:
            rel_path = file_path.relative_to(self.root)
        except ValueError:
            return "UNKNOWN"
        
        parts = rel_path.parts
        if not parts:
            return "UNKNOWN"
        
        file_name = file_path.name.lower()
        ext = file_path.suffix.lower()
        
        # Получаем размер файла
        try:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            size_kb = file_path.stat().st_size / 1024
        except OSError:
            size_mb = 0
            size_kb = 0
        
        # 1. Проверяем junk_folders (приоритет — мусор детектим первым)
        first_folder = parts[0].lower() if len(parts) > 1 else None
        if first_folder and first_folder in self.junk_folders:
            logger.debug(f"[Classifier] {file_path.name} -> JUNK (folder: {first_folder})")
            return "JUNK"
        
        # 2. Проверяем критичные файлы в корне
        if len(parts) == 1 and file_name in self.critical_files:
            logger.debug(f"[Classifier] {file_path.name} -> CRITICAL (root file)")
            return "CRITICAL"
        
        # 3. Проверяем code_folders
        if first_folder and first_folder in self.code_folders:
            # Код в папках src/, app/, api/ и т.д.
            if ext in self.cfg.code_extensions:
                logger.debug(f"[Classifier] {file_path.name} -> CODE (folder: {first_folder})")
                return "CODE"
        
        # 4. Проверяем паттерны мусорных файлов (FULL_PROJECT_CODE.txt и т.д.)
        import fnmatch
        for pattern in self.cfg.junk_file_patterns:
            if fnmatch.fnmatch(file_path.name, pattern) or fnmatch.fnmatch(file_name, pattern.lower()):
                logger.debug(f"[Classifier] {file_path.name} -> JUNK (pattern: {pattern})")
                return "JUNK"
        
        # 5. Проверяем большие .txt файлы
        txt_limit_kb = self.cfg.txt_max_size_kb
        if ext == ".txt" and size_kb > txt_limit_kb:
            logger.debug(f"[Classifier] {file_path.name} -> JUNK (txt > {txt_limit_kb}KB)")
            return "JUNK"
        
        # 6. Проверяем размер для корзины
        if size_mb > self.cfg.max_trash_size_mb:
            logger.debug(f"[Classifier] {file_path.name} -> TRASH (size > {self.cfg.max_trash_size_mb}MB)")
            return "TRASH"
        
        # 7. Проверяем подозрительные слова в названии
        for word in self.SUSPICIOUS_WORDS:
            if word in file_name:
                # Если файл большой и с подозрительным именем — в корзину
                if size_mb > 0.5:  # > 500KB
                    logger.debug(f"[Classifier] {file_path.name} -> TRASH (suspicious: {word})")
                    return "TRASH"
        
        # 8. Проверяем garbage расширения
        if ext in self.cfg.garbage_extensions:
            if size_mb > self.cfg.max_asset_size_mb:
                logger.debug(f"[Classifier] {file_path.name} -> JUNK (garbage ext, size > limit)")
                return "JUNK"
        
        # 9. Проверяем data расширения (.csv, .json, .xml)
        if ext in self.cfg.data_extensions:
            # Data файлы игнорируются если > data_min_size_kb И < max_trash_size_mb
            # (очень большие идут в trash, маленькие остаются)
            data_min_size_kb = self.cfg.data_min_size_kb
            if size_kb > data_min_size_kb and size_mb <= self.cfg.max_trash_size_mb:
                logger.debug(f"[Classifier] {file_path.name} -> DATA (data ext, {size_kb:.1f}KB > {data_min_size_kb}KB)")
                return "DATA"
        
        # 10. Код в корне — защищаем
        if len(parts) == 1 and ext in {".py", ".js", ".ts"}:
            logger.debug(f"[Classifier] {file_path.name} -> CODE (root code file)")
            return "CODE"
        
        # Если ничего не подошло — неизвестно, оставляем как есть
        return "UNKNOWN"
    
    def get_action_description(self, action: FileAction) -> str:
        """Возвращает человекочитаемое описание действия."""
        descriptions = {
            "CODE": "Code file - protected",
            "CRITICAL": "Critical file - protected",
            "JUNK": "Junk - add to .cursorignore + .gitignore",
            "DATA": "Project data - add to .gitignore only",
            "TRASH": "Trash - move to _trash/",
            "UNKNOWN": "Unknown - leave as is"
        }
        return descriptions.get(action, "Unknown action")

