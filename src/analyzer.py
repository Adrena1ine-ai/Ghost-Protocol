import subprocess
import os
from pathlib import Path
from typing import Tuple, Optional, List
from .config import Config
from .core import logger

# Список расширений, которые мы проверяем (код)
TARGET_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx"}

class CodeAnalyzer:
    def __init__(self, root: Path):
        self.root = root

    def run_lint(self) -> Tuple[bool, str]:
        """Запускает Ruff. Проверяет только файлы с расширениями кода."""
        # 1. Собираем список файлов
        target_files = []
        try:
            cfg = Config.get()
            for root_dir, dirs, files in os.walk(self.root):
                # Фильтруем папки (чтобы не искать в venv и т.д.)
                dirs[:] = [d for d in dirs if d not in cfg.skip_dirs and not d.startswith(".")]
                for file in files:
                    file_path = Path(root_dir) / file
                    if file_path.suffix.lower() in TARGET_EXTENSIONS:
                        target_files.append(str(file_path))
        except OSError:
            pass

        # 2. Запускаем Ruff
        if not target_files:
            return True, "No code files to check."
        
        cmd = ["ruff", "check"] + target_files
        try:
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, "Lint passed."
            else:
                # Ruff выводит ошибки в stderr
                return False, result.stderr.strip() or "Lint errors found."
        except FileNotFoundError:
            return None, "Ruff not installed."
        except Exception as e:
            return None, str(e)

    def analyze_complexity(self) -> Tuple[bool, str]:
        """Запускает Radon для подсчета сложности (CC)."""
        # Radon умеет работать с каталогами, собираем все папки рекурсивно
        target_dirs = []
        try:
            cfg = Config.get()
            # Рекурсивный обход всех папок (как в run_lint)
            for root_dir, dirs, files in os.walk(self.root):
                # Фильтруем папки (чтобы не искать в venv и т.д.)
                dirs[:] = [d for d in dirs if d not in cfg.skip_dirs and not d.startswith(".")]
                # Добавляем текущую папку
                target_dirs.append(root_dir)
        except OSError:
            pass

        if not target_dirs:
            return True, "Complexity OK."

        cmd = ["radon", "cc"] + target_dirs
        try:
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=10)
            output = result.stdout
            
            # Парсим вывод (очень упрощенно)
            issues = []
            for line in output.split('\n'):
                if 'B:' in line: # B - High complexity block
                    issues.append(line.strip())
            
            if issues:
                return False, f"Found {len(issues)} complex blocks."
            else:
                return True, "Complexity is OK."
        except FileNotFoundError:
            return None, "Radon not installed."
        except Exception as e:
            return None, str(e)

    def full_check(self) -> str:
        """Полная проверка (Lint + Complexity)"""
        lint_ok, lint_msg = self.run_lint()
        comp_ok, comp_msg = self.analyze_complexity()
        
        report = []
        if lint_ok:
            report.append("[OK] Lint OK")
        elif lint_ok is None:
            report.append(f"[WARN] Lint: {lint_msg}")
        else:
            report.append(f"[FAIL] Lint Failed: {lint_msg}")
            
        if comp_ok:
            report.append("[OK] Complexity OK")
        elif comp_ok is None:
            report.append(f"[WARN] Complexity: {comp_msg}")
        else:
            report.append(f"[FAIL] High Complexity")
            
        return "\n".join(report)
