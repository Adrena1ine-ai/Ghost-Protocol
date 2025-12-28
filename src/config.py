import json
import copy
import logging
import os
from pathlib import Path
from typing import Set, Dict, Any, List, Optional

logger = logging.getLogger("ghost.config")

VERSION = "2.0.0"

DEFAULT_CONFIG = {
    "limits": {
        "max_asset_size_mb": 1.0,
        "max_code_size_mb": 0.5,
        "debounce_seconds": 0.5,
        "bytes_per_token": 4,
        "max_trash_size_mb": 2.0,  # Файлы больше 2 МБ автоматически в _trash
        "txt_max_size_kb": 50,  # .txt файлы больше 50KB считаются мусором
        "data_min_size_kb": 100  # Data файлы больше 100KB игнорируются в .gitignore (но видны для AI)
    },
    "skip_dirs": [
        "venv", ".venv", "env", ".env", "node_modules", "__pycache__", 
        ".git", ".idea", ".vscode", ".DS_Store", "coverage", "dist", "build",
        "target", "out", "bin", "obj", "lib", ".cursor", ".logs", "_trash"
    ],
    "safe_zones": {
        "code_folders": [
            "src", "app", "api", "core", "utils", "handlers", "services",
            "routes", "models", "views", "schemas", "controllers", "lib",
            "modules", "components", "pages", "features", "hooks"
        ],
        "junk_folders": [
            "assets", "static", "media", "img", "images", "icons",
            "data", "input", "output", "dump", "dumps", "backup", "backups",
            "logs", "log", "temp", "tmp", "cache", ".cache",
            "_trash", "trash", "old", "archive", "archives",
            "uploads", "downloads", "files", "attachments",
            "fonts", "audio", "video", "music", "sounds"
        ],
        "critical_files": [
            "main.py", "app.py", "config.py", "manage.py", "settings.py",
            "wsgi.py", "asgi.py", "setup.py", "pyproject.toml", "setup.cfg",
            "requirements.txt", "package.json", "tsconfig.json",
            ".env", ".env.example", "dockerfile", "docker-compose.yml",
            "makefile", "readme.md", "license", "changelog.md"
        ]
    },
    "junk_file_patterns": [  # Паттерны имен файлов, которые всегда должны быть в игноре
        "*FULL_PROJECT*.txt",
        "*PROJECT_SOURCE*.txt",
        "*SOURCE_CODE*.txt",
        "*COMPLETE_CODE*.txt",
        "*ALL_CODE*.txt",
        "*DUMP*.txt",
        "*BACKUP*.txt"
    ],
    "extensions": {
        "garbage": [  # System Junk: игнорируется везде (.gitignore + .cursorignore)
            ".log", ".sqlite", ".db",
            ".zip", ".rar", ".7z", ".mp4", ".mov", ".avi", ".mp3", 
            ".pdf", ".exe", ".dll", ".bin", ".dat", ".tmp", ".bak", ".swp", 
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
            ".tar.gz"
        ],
        "data": [  # Project Data: только .gitignore (не .cursorignore), чтобы ИИ мог использовать
            ".csv", ".tsv", ".json", ".xml"
        ],
        "code": [".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", 
                ".java", ".c", ".cpp", ".rs", ".go", ".php", ".rb", ".md", ".txt", ".yml", ".yaml"]
    },
    "ai": {
        "provider": "gemini",
        "model": "gemini-1.5-flash", # Самый быстрый и дешевый для review
        "api_key": "", # Вставь свой ключ в ghost_config.json
        "temperature": 0.2 # Низкая температура для точности кода
    },
    "system": {
        "trash_folder": "_trash",
        "auto_install_deps": True # Автоматически устанавливать ruff/radon
    }
}

class Config:
    _instance: Optional['Config'] = None

    def __init__(self, root: Path):
        self.root = root
        self._data = copy.deepcopy(DEFAULT_CONFIG)
        self._rebuild_caches()
        self._load_user_config()
        self._setup_environment()
    
    def _setup_environment(self):
        """Создает папку _trash и добавляет её в skip_dirs"""
        trash_dir = self.root / self._data['system']['trash_folder']
        if not trash_dir.exists():
            trash_dir.mkdir(exist_ok=True)
            logger.info(f"[Setup] Created trash folder: {trash_dir.name}")
        
        # Добавляем в список пропускаемых папок, чтобы не сканировать мусор
        if self._data['system']['trash_folder'] not in self._data['skip_dirs']:
            self._data['skip_dirs'].append(self._data['system']['trash_folder'])
            # Пересобираем кэш
            self._skip_dirs_cache = set(self._data['skip_dirs'])

    def _rebuild_caches(self):
        self._skip_dirs_cache: Set[str] = set(self._data['skip_dirs'])
        self._garbage_ext_cache: Set[str] = set(self._data['extensions']['garbage'])
        self._data_ext_cache: Set[str] = set(self._data['extensions'].get('data', []))
        self._code_ext_cache: Set[str] = set(self._data['extensions']['code'])
        self._junk_file_patterns: List[str] = self._data.get('junk_file_patterns', [])
        
        # Safe Zones
        safe_zones = self._data.get('safe_zones', {})
        self._code_folders: Set[str] = set(safe_zones.get('code_folders', []))
        self._junk_folders: Set[str] = set(safe_zones.get('junk_folders', []))
        self._critical_files: Set[str] = set(f.lower() for f in safe_zones.get('critical_files', []))

    def _load_user_config(self):
        config_path = self.root / "ghost_config.json"
        if not config_path.exists():
            self._create_default_config(config_path)
            return
            
        try:
            user_cfg = json.loads(config_path.read_text())
            
            if 'skip_dirs' in user_cfg:
                self._data['skip_dirs'] = list(set(
                    self._data['skip_dirs'] + user_cfg['skip_dirs']
                ))
            
            if 'limits' in user_cfg:
                self._data['limits'].update(user_cfg['limits'])
            
            if 'extensions' in user_cfg:
                u_ext = user_cfg['extensions']
                if 'garbage' in u_ext:
                    self._data['extensions']['garbage'] = list(set(
                        self._data['extensions']['garbage'] + u_ext['garbage']
                    ))
                if 'data' in u_ext:
                    self._data['extensions']['data'] = list(set(
                        self._data['extensions'].get('data', []) + u_ext['data']
                    ))
                if 'code' in u_ext:
                    self._data['extensions']['code'] = list(set(
                        self._data['extensions']['code'] + u_ext['code']
                    ))

            if 'ai' in user_cfg:
                self._data['ai'].update(user_cfg['ai'])

            if 'system' in user_cfg:
                self._data['system'].update(user_cfg['system'])
            
            if 'junk_file_patterns' in user_cfg:
                self._data['junk_file_patterns'] = list(set(
                    self._data.get('junk_file_patterns', []) + user_cfg['junk_file_patterns']
                ))
            
            self._rebuild_caches()
            
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")

    def _create_default_config(self, path: Path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            logger.info(f"Created default config at {path}")
        except IOError:
            pass

    @classmethod
    def init(cls, root: Path):
        if cls._instance is None:
            cls._instance = cls(root)

    @classmethod
    def get(cls) -> 'Config':
        if cls._instance is None:
            raise RuntimeError("Config not initialized. Call Config.init(root) first.")
        return cls._instance

    @property
    def max_asset_size_mb(self) -> float: return self._data['limits']['max_asset_size_mb']
    @property
    def max_code_size_mb(self) -> float: return self._data['limits']['max_code_size_mb']
    @property
    def debounce_seconds(self) -> float: return self._data['limits']['debounce_seconds']
    @property
    def bytes_per_token(self) -> int: return self._data['limits']['bytes_per_token']
    @property
    def max_trash_size_mb(self) -> float: return self._data['limits']['max_trash_size_mb']
    @property
    def txt_max_size_kb(self) -> int: return self._data['limits'].get('txt_max_size_kb', 50)
    @property
    def data_min_size_kb(self) -> int: return self._data['limits'].get('data_min_size_kb', 100)
    
    @property
    def skip_dirs(self) -> Set[str]: return self._skip_dirs_cache
    @property
    def garbage_extensions(self) -> Set[str]: return self._garbage_ext_cache
    @property
    def data_extensions(self) -> Set[str]: return self._data_ext_cache
    @property
    def code_extensions(self) -> Set[str]: return self._code_ext_cache
    @property
    def junk_file_patterns(self) -> List[str]: return self._junk_file_patterns
    
    # Safe Zones
    @property
    def code_folders(self) -> Set[str]: return self._code_folders
    @property
    def junk_folders(self) -> Set[str]: return self._junk_folders
    @property
    def critical_files(self) -> Set[str]: return self._critical_files

    @property
    def gitignore_file(self) -> str: return ".gitignore"
    @property
    def cursorignore_file(self) -> str: return ".cursorignore"
    @property
    def cache_file(self) -> str: return ".ghost_stats.json"
    @property
    def ghost_tag(self) -> str: return "# ghost: auto"
    
    # AI Config
    @property
    def ai_provider(self) -> str: return self._data['ai']['provider']
    @property
    def ai_model(self) -> str: return self._data['ai']['model']
    @property
    def ai_api_key(self) -> str: return self._data['ai']['api_key']
    @property
    def ai_temperature(self) -> float: return self._data['ai']['temperature']

    # System Config
    @property
    def trash_folder(self) -> str: return self._data['system']['trash_folder']
    @property
    def auto_install_deps(self) -> bool: return True