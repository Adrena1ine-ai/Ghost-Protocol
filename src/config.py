import json
import copy
import logging
from pathlib import Path
from typing import Set, Dict, Any, List, Optional

logger = logging.getLogger("ghost.config")

VERSION = "1.0.2"

DEFAULT_CONFIG = {
    "limits": {
        "max_asset_size_mb": 1.0,
        "max_code_size_mb": 0.5,
        "debounce_seconds": 0.5,
        "bytes_per_token": 4
    },
    "skip_dirs": [
        "venv", ".venv", "env", ".env", "node_modules", "__pycache__", 
        ".git", ".idea", ".vscode", ".DS_Store", "coverage", "dist", "build",
        "target", "out", "bin", "obj", "lib", ".cursor", ".logs"
    ],
    "extensions": {
        "garbage": [
            ".log", ".sqlite", ".db", ".csv", ".tsv", 
            ".zip", ".rar", ".7z", ".mp4", ".mov", ".avi", ".mp3", 
            ".pdf", ".exe", ".dll", ".bin", ".dat", ".tmp", ".bak", ".swp", 
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
            ".tar.gz"
        ],
        "code": [".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", 
                ".java", ".c", ".cpp", ".rs", ".go", ".php", ".rb", ".md", ".txt", ".yml", ".yaml", ".json"]
    }
}

class Config:
    _instance: Optional['Config'] = None

    def __init__(self, root: Path):
        self.root = root
        self._data = copy.deepcopy(DEFAULT_CONFIG)
        self._rebuild_caches()
        self._load_user_config()

    def _rebuild_caches(self):
        self._skip_dirs_cache: Set[str] = set(self._data['skip_dirs'])
        self._garbage_ext_cache: Set[str] = set(self._data['extensions']['garbage'])
        self._code_ext_cache: Set[str] = set(self._data['extensions']['code'])

    def _load_user_config(self):
        config_path = self.root / "ghost_config.json"
        if not config_path.exists():
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
                if 'code' in u_ext:
                    self._data['extensions']['code'] = list(set(
                        self._data['extensions']['code'] + u_ext['code']
                    ))
            
            self._rebuild_caches()
            
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")

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
    def skip_dirs(self) -> Set[str]: return self._skip_dirs_cache
    @property
    def garbage_extensions(self) -> Set[str]: return self._garbage_ext_cache
    @property
    def code_extensions(self) -> Set[str]: return self._code_ext_cache

    @property
    def gitignore_file(self) -> str: return ".gitignore"
    @property
    def cursorignore_file(self) -> str: return ".cursorignore"
    @property
    def cache_file(self) -> str: return ".ghost_stats.json"
    @property
    def ghost_tag(self) -> str: return "# ghost: auto"