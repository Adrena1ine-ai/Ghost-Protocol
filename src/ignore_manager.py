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

    def add_entries(self, paths_to_add: Set[str]):
        """Add paths to ignore files with safety tags."""
        if not paths_to_add: return

        total_added_count = 0

        for target in self.targets:
            target.touch(exist_ok=True)
            
            with interprocess_lock(target):
                content = target.read_text(encoding="utf-8")
                current_lines = set(content.splitlines())
                
                new_entries = []
                for p in paths_to_add:
                    ghost_line = f"{p}  {self.cfg.ghost_tag}"
                    if ghost_line not in current_lines and p not in current_lines:
                        new_entries.append(ghost_line)

                if new_entries:
                    if content and not content.endswith('\n'): content += '\n'
                    content += "\n".join(new_entries) + "\n"
                    atomic_write(target, content)
                    total_added_count += len(new_entries)
        
        if total_added_count > 0:
            # Since we write to both files, total_added_count will be sum of entries in both files.
            # If entries are identical in both files, it's effectively 2x paths_to_add.
            # We'll just log the action fact.
            logger.info(f"[Ghost] Updated ignore files with {len(paths_to_add)} new assets.")

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