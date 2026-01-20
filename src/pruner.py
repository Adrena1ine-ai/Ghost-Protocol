from pathlib import Path
from .ignore_manager import IgnoreFileManager
from .core import logger

class Pruner:
    def __init__(self, root: Path):
        self.root = root
        self.ignore_mgr = IgnoreFileManager(root)

    def cleanup(self):
        """Run cleanup on all ignore files"""
        try:
            self.ignore_mgr.prune_stale()
        except Exception as e:
            logger.error(f"Prune failed: {e}")
            raise