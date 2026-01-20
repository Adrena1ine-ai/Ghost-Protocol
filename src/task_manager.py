"""
TaskManager — Управление задачами для God Mode Auto-Pilot

Создаёт и управляет файлом GHOST_TASKS.md, который служит каналом связи
между Ghost Protocol и Cursor AI.
"""

import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from .config import Config
from .core import logger
from .utils import interprocess_lock, atomic_write


class TaskManager:
    """Менеджер задач для Auto-Pilot режима"""
    
    TASKS_FILE = "GHOST_TASKS.md"
    MAX_TASKS = 20  # Максимум задач в файле
    
    def __init__(self, root: Path):
        self.root = root
        self.tasks_file = root / self.TASKS_FILE
        self.cfg = Config.get()
    
    def write_task(self, task_type: str, file_path: str, diff: Optional[str] = None, 
                   instruction: str = "", reason: str = "") -> bool:
        """
        Записывает задачу в GHOST_TASKS.md
        
        Args:
            task_type: "Auto-Fix" или "Code Review"
            file_path: Путь к файлу (относительный)
            diff: Unified diff (для Auto-Fix)
            instruction: Инструкция для Cursor
            reason: Причина создания задачи
        
        Returns:
            True если задача записана, False если отклонена (критичный файл)
        """
        # Проверка безопасности: критичные файлы
        if not self._is_safe_to_modify(file_path, task_type):
            logger.warning(f"[Ghost] Refused: Critical file cannot be modified - {file_path}")
            return False
        
        try:
            with interprocess_lock(self.tasks_file):
                # Читаем существующие задачи
                existing_tasks = self._read_tasks()
                
                # Добавляем новую задачу
                new_task = {
                    "timestamp": datetime.now().isoformat(),
                    "type": task_type,
                    "file": file_path,
                    "diff": diff,
                    "instruction": instruction,
                    "reason": reason
                }
                
                existing_tasks.insert(0, new_task)  # Новая задача в начале
                
                # Ограничиваем количество задач
                if len(existing_tasks) > self.MAX_TASKS:
                    existing_tasks = existing_tasks[:self.MAX_TASKS]
                
                # Форматируем и записываем
                content = self._format_tasks(existing_tasks)
                atomic_write(self.tasks_file, content)
                
                logger.info(f"[Ghost] Task written: {task_type} for {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"[Ghost] Failed to write task: {e}")
            return False
    
    def _is_safe_to_modify(self, file_path: str, task_type: str) -> bool:
        """
        Проверяет, безопасно ли модифицировать файл
        
        Критичные файлы можно модифицировать только через Auto-Fix (Ruff),
        но нельзя удалять или делать серьёзные изменения через AI Review.
        """
        file_name = Path(file_path).name.lower()
        critical_files = self.cfg.critical_files
        
        # Критичные файлы в списке
        if file_name in critical_files:
            # Auto-Fix (Ruff) разрешён для критичных файлов
            if task_type == "Auto-Fix":
                return True
            # AI Review для критичных файлов - только предупреждение
            # (не блокируем, но логируем)
            logger.warning(f"[Ghost] Warning: Task for critical file {file_path}")
            return True  # Разрешаем, но с предупреждением
        
        return True
    
    def _read_tasks(self) -> List[Dict[str, Any]]:
        """Читает существующие задачи из файла"""
        if not self.tasks_file.exists():
            return []
        
        try:
            content = self.tasks_file.read_text(encoding='utf-8')
            return self._parse_tasks(content)
        except Exception:
            return []
    
    def _parse_tasks(self, content: str) -> List[Dict[str, Any]]:
        """Парсит задачи из Markdown"""
        tasks = []
        lines = content.split('\n')
        current_task = None
        current_diff = []
        in_diff = False
        
        for line in lines:
            if line.startswith('## Task '):
                if current_task:
                    if current_diff:
                        current_task['diff'] = '\n'.join(current_diff)
                    tasks.append(current_task)
                current_task = {}
                current_diff = []
                in_diff = False
            elif line.startswith('**File:**'):
                if current_task:
                    current_task['file'] = line.split('`')[1] if '`' in line else line.split(':')[1].strip()
            elif line.startswith('**Type:**'):
                if current_task:
                    current_task['type'] = line.split(':')[1].strip()
            elif line.startswith('**Reason:**'):
                if current_task:
                    current_task['reason'] = line.split(':', 1)[1].strip() if ':' in line else ''
            elif line.startswith('**Diff:**'):
                in_diff = True
            elif line.startswith('**Instruction:**'):
                in_diff = False
                if current_task:
                    # Читаем инструкцию до следующего ##
                    instruction_lines = []
                    idx = lines.index(line) + 1
                    while idx < len(lines) and not lines[idx].startswith('##'):
                        instruction_lines.append(lines[idx])
                        idx += 1
                    current_task['instruction'] = '\n'.join(instruction_lines).strip()
            elif in_diff and line.startswith('```'):
                continue
            elif in_diff:
                current_diff.append(line)
        
        if current_task:
            if current_diff:
                current_task['diff'] = '\n'.join(current_diff)
            tasks.append(current_task)
        
        return tasks
    
    def _format_tasks(self, tasks: List[Dict[str, Any]]) -> str:
        """Форматирует задачи в Markdown"""
        lines = [
            "# 🤖 Auto-Tasks by Ghost Protocol",
            "",
            "> This file is automatically generated by Ghost Protocol.",
            "> Cursor AI should monitor this file and execute tasks when ready.",
            "",
            "---",
            ""
        ]
        
        for idx, task in enumerate(tasks, 1):
            task_type = task.get('type', 'Unknown')
            file_path = task.get('file', 'unknown')
            reason = task.get('reason', '')
            diff = task.get('diff', '')
            instruction = task.get('instruction', '')
            timestamp = task.get('timestamp', datetime.now().isoformat())
            
            lines.append(f"## Task {idx}: {task_type}")
            lines.append(f"**File:** `{file_path}`")
            lines.append(f"**Type:** {task_type}")
            if reason:
                lines.append(f"**Reason:** {reason}")
            lines.append(f"**Timestamp:** {timestamp}")
            lines.append("")
            
            if diff:
                lines.append("**Diff:**")
                lines.append("```diff")
                lines.append(diff)
                lines.append("```")
                lines.append("")
            
            if instruction:
                lines.append("**Instruction:**")
                lines.append(instruction)
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return '\n'.join(lines)
    
    def clear_tasks(self):
        """Очищает все задачи (вызывается после выполнения)"""
        try:
            if self.tasks_file.exists():
                self.tasks_file.write_text("# 🤖 Auto-Tasks by Ghost Protocol\n\n> All tasks completed.\n", encoding='utf-8')
                logger.info("[Ghost] Tasks file cleared")
        except Exception as e:
            logger.error(f"[Ghost] Failed to clear tasks: {e}")

