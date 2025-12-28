import subprocess
import re
from pathlib import Path
from .config import Config
from .core import logger

class CodeAnalyzer:
    def __init__(self, root: Path):
        self.root = root

    def run_lint(self, files_to_check=None):
        """Запускает Ruff. Если files_to_check None — проверяет весь проект."""
        cmd = ["ruff", "check"]
        if files_to_check:
            cmd.extend(files_to_check)
        
        try:
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
            if result.returncode == 0:
                return True, "Lint passed."
            else:
                # Ruff выводит ошибки в stderr
                return False, result.stderr
        except FileNotFoundError:
            return None, "Ruff not installed."
        except Exception as e:
            return None, str(e)

    def analyze_complexity(self):
        """Запускает Radon для подсчета сложности (CC)."""
        cmd = ["radon", "cc", ".", "-a"]
        try:
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
            output = result.stdout
            
            # Парсим вывод Radon (очень упрощенно)
            # Формат: path/to/file.py - A: 10 (Complexity)
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

    def full_check(self):
        """Полная проверка (Lint + Complexity)"""
        lint_ok, lint_msg = self.run_lint()
        comp_ok, comp_msg = self.analyze_complexity()
        
        report = []
        if lint_ok:
            report.append("✅ Lint OK")
        elif lint_ok is None:
            report.append(f"⚠️ Lint: {lint_msg}")
        else:
            report.append(f"❌ Lint Failed")
            
        if comp_ok:
            report.append("✅ Complexity OK")
        elif comp_ok is None:
            report.append(f"⚠️ Complexity: {comp_msg}")
        else:
            report.append(f"❌ High Complexity")
            
        return "\n".join(report)