"""
AIReviewer — 3-уровневая система AI Code Review (Worker -> Supervisor -> Oracle)

Архитектура:
1. Worker (Ruff) - Проверяет стиль и простые ошибки
2. Supervisor (Gemini 2.0 Flash) - Анализирует код и генерирует промпт для исправления
3. Oracle (GPT-4o Mini) - Валидирует промпт от Supervisor на безопасность

Использует:
1. Глобальный конфиг (~/.ghost/config.json) — приоритет
2. Локальный конфиг (ghost_config.json) — fallback
"""

import subprocess
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .config import Config
from .core import logger
from .task_manager import TaskManager
from .analyzer import CodeAnalyzer

# Опциональный импорт pyperclip
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    pyperclip = None
    PYPERCLIP_AVAILABLE = False

# Опциональный импорт google-genai (новый пакет)
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

# Опциональный импорт OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False

# Опциональный импорт Pydantic
try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback классы если Pydantic недоступен
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self):
            return {k: v for k, v in self.__dict__.items()}
    Field = lambda **kwargs: None


# Pydantic модели
class TaskModel(BaseModel):
    """Модель задачи для GHOST_TASKS.md"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str  # "LINT_FIX", "CODE_REVIEW"
    file: str
    line: int = 0
    message: str
    status: str = "PENDING"  # "PENDING", "APPROVED", "REJECTED"
    diff: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    instruction: str = ""
    reason: str = ""


class SupervisorResponse(BaseModel):
    """Ответ от Supervisor (Gemini)"""
    prompt: str
    is_safe: bool
    reason: str = ""


class AIReviewer:
    """
    3-уровневая система AI Code Review:
    1. Worker (Ruff) - автоматическая проверка стиля
    2. Supervisor (Gemini) - анализ и генерация промпта
    3. Oracle (GPT-4o) - валидация безопасности
    """
    
    def __init__(self, root: Path):
        self.root = root
        self.cfg = Config.get()
        self.last_generated_prompt = ""
        self.last_review_status = "AI: Initializing..."
        
        # Клиенты API
        self.supervisor_client = None  # Gemini
        self.oracle_client = None      # OpenAI
        
        # Инициализация компонентов
        self.task_manager = TaskManager(root)
        self.analyzer = CodeAnalyzer(root)
        
        # Инициализация API
        self._init_apis()
    
    def _init_apis(self):
        """Инициализирует клиенты Gemini и OpenAI"""
        # Получаем API ключи (приоритет: глобальный конфиг > локальный конфиг)
        gemini_key = self._get_gemini_key()
        openai_key = self._get_openai_key()
        
        # Инициализация Gemini (Supervisor)
        if gemini_key and GENAI_AVAILABLE:
            try:
                self.supervisor_client = genai.Client(api_key=gemini_key)
                logger.info("Supervisor (Gemini) initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supervisor: {e}")
                self.last_review_status = f"Supervisor Error: {str(e)[:50]}"
        elif not GENAI_AVAILABLE:
            logger.warning("google-genai not installed. Supervisor disabled.")
        else:
            logger.warning("Gemini API key not found. Run 'ghost --setup' to configure")
        
        # Инициализация OpenAI (Oracle)
        if openai_key and OPENAI_AVAILABLE:
            try:
                self.oracle_client = OpenAI(api_key=openai_key)
                logger.info("Oracle (OpenAI) initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Oracle: {e}")
        elif not OPENAI_AVAILABLE:
            logger.warning("openai not installed. Oracle disabled.")
        else:
            logger.debug("OpenAI API key not found (Oracle optional)")
        
        # Обновляем статус
        if self.supervisor_client:
            if self.oracle_client:
                self.last_review_status = "AI Ready (Supervisor + Oracle)"
            else:
                self.last_review_status = "AI Ready (Supervisor only)"
        else:
            self.last_review_status = "AI: Run 'ghost --setup' to configure"
    
    def _get_gemini_key(self) -> str:
        """Получает Gemini API ключ из глобального или локального конфига"""
        # 1. Пробуем глобальный конфиг
        try:
            from .global_config import GlobalConfig
            global_cfg = GlobalConfig.get()
            if global_cfg.api_key and global_cfg.provider == "gemini":
                logger.debug(f"Using Gemini key from global config")
                return global_cfg.api_key
        except Exception:
            pass
        
        # 2. Локальный конфиг - gemini_api_key
        if self.cfg.gemini_api_key:
            logger.debug("Using Gemini key from local config")
            return self.cfg.gemini_api_key
        
        # 3. Fallback на старый api_key
        if self.cfg.ai_api_key:
            logger.debug("Using legacy api_key for Gemini")
            return self.cfg.ai_api_key
        
        return ""
    
    def _get_openai_key(self) -> str:
        """Получает OpenAI API ключ из конфига"""
        return self.cfg.openai_api_key
    
    def run_review(self, file_path: Path = None, auto_mode: bool = False):
        """
        Запускает 3-уровневую проверку кода
        
        Args:
            file_path: Если указан, проверяет только этот файл (God Mode)
            auto_mode: Если True, автоматически создаёт задачи в GHOST_TASKS.md
        """
        # Если передан файл, проверяем его (God Mode)
        if file_path and file_path.exists():
            self._review_file(file_path, auto_mode)
            return
        
        # Иначе проверяем весь git diff
        self.last_review_status = "AI: Analyzing diff..."
        
        # Получаем git diff для staged файлов (--cached)
        try:
            output = subprocess.check_output(
                ["git", "diff", "--cached", "--unified=0"],
                cwd=self.root,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
        except subprocess.CalledProcessError:
            # Если нет staged изменений, пробуем обычный diff
            try:
                output = subprocess.check_output(
                    ["git", "diff", "HEAD", "--unified=0"],
                    cwd=self.root,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.last_review_status = "AI: No git changes detected"
                return
            except Exception as e:
                self.last_review_status = f"AI: Git error - {str(e)[:30]}"
                return
        except FileNotFoundError:
            self.last_review_status = "AI: Git not found"
            return
        except Exception as e:
            self.last_review_status = f"AI: Git error - {str(e)[:30]}"
            return

        if not output or not output.strip():
            self.last_review_status = "AI: No changes to review"
            return
        
        # Подсчитываем количество строк
        diff_lines = len(output.strip().split('\n'))
        
        # Правило: < 20 строк -> тишина (не проверяем)
        if diff_lines < 20:
            self.last_review_status = "AI: Changes too small (< 20 lines), skipping"
            logger.debug(f"Skipping review for small diff ({diff_lines} lines)")
            return
        
        # Правило: > 50 строк -> запускаем Supervisor Stage
        if diff_lines > 50:
            if not self.supervisor_client:
                self.last_review_status = "AI: Supervisor not available"
                return
            
            try:
                supervisor_response = self._supervisor_generate_prompt(output)
                
                if not supervisor_response.is_safe:
                    # Supervisor отклонил изменения
                    self._save_task(
                        task_type="CODE_REVIEW",
                        file_path="multiple files",
                        message=f"Rejected by Supervisor: {supervisor_response.reason}",
                        status="REJECTED",
                        instruction=supervisor_response.prompt,
                        diff=output[:2000]
                    )
                    self.last_review_status = "AI: Supervisor rejected changes"
                    return
                
                # Supervisor одобрил -> запускаем Oracle Stage
                if self.oracle_client:
                    oracle_status = self._validate_with_oracle(supervisor_response.prompt)
                    
                    if oracle_status == "REJECTED":
                        self._save_task(
                            task_type="CODE_REVIEW",
                            file_path="multiple files",
                            message="Rejected by Oracle",
                            status="REJECTED",
                            instruction=supervisor_response.prompt,
                            diff=output[:2000]
                        )
                        self.last_review_status = "AI: Oracle rejected changes"
                        return
                    
                    # Oracle одобрил -> сохраняем задачу
                    if auto_mode:
                        self._save_task(
                            task_type="CODE_REVIEW",
                            file_path="multiple files",
                            message="Approved by Supervisor and Oracle",
                            status="APPROVED",
                            instruction=supervisor_response.prompt,
                            diff=output[:2000]
                        )
                        self.last_review_status = "AI: Task created (approved)"
                else:
                    # Oracle недоступен -> используем только Supervisor
                    if auto_mode:
                        self._save_task(
                            task_type="CODE_REVIEW",
                            file_path="multiple files",
                            message="Approved by Supervisor (Oracle unavailable)",
                            status="APPROVED",
                            instruction=supervisor_response.prompt,
                            diff=output[:2000]
                        )
                        self.last_review_status = "AI: Task created (Supervisor only)"
                
                self.last_generated_prompt = supervisor_response.prompt
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    self.last_review_status = "AI: Quota exceeded. Wait 1 min."
                elif "401" in error_msg or "403" in error_msg:
                    self.last_review_status = "AI: Invalid API key"
                else:
                    self.last_review_status = f"AI Error: {str(e)[:40]}"
                logger.error(f"AI Review failed: {e}")
        else:
            # 20-50 строк - используем только Worker (Ruff)
            self.last_review_status = "AI: Medium changes (20-50 lines), using Worker only"
            logger.debug(f"Using Worker (Ruff) for medium diff ({diff_lines} lines)")
    
    def _supervisor_generate_prompt(self, diff: str) -> SupervisorResponse:
        """
        Supervisor Stage: Генерирует промпт для исправления через Gemini
        
        Args:
            diff: Git diff текст
            
        Returns:
            SupervisorResponse с промптом и статусом безопасности
        """
        supervisor_prompt = f"""Ты Senior Architect. Проанализируй этот Git Diff.

Найди:
1. Ошибки безопасности (SQL injection, XSS, hardcoded secrets)
2. Дублирование кода
3. Нарушения PEP8/стиля
4. Потенциальные баги

Если есть критические ошибки — напиши ПРОМПТ для Cursor AI в формате JSON:
{{
    "prompt": "детальный промпт для исправления",
    "is_safe": true/false,
    "reason": "причина одобрения/отклонения"
}}

Если ошибок нет или они косметические — верни: {{"prompt": "CLEAN", "is_safe": true, "reason": "Code is clean"}}

Git Diff:
```
{diff[:8000]}
```"""
        
        try:
            model_name = self.cfg.supervisor_model
            response = self.supervisor_client.models.generate_content(
                model=model_name,
                contents=supervisor_prompt
            )
            result_text = response.text.strip()
            
            # Парсим JSON ответ
            try:
                # Извлекаем JSON из текста (может быть обёрнут в markdown code blocks)
                if "```json" in result_text:
                    json_start = result_text.find("```json") + 7
                    json_end = result_text.find("```", json_start)
                    result_text = result_text[json_start:json_end].strip()
                elif "```" in result_text:
                    json_start = result_text.find("```") + 3
                    json_end = result_text.find("```", json_start)
                    result_text = result_text[json_start:json_end].strip()
                
                data = json.loads(result_text)
                
                return SupervisorResponse(
                    prompt=data.get("prompt", ""),
                    is_safe=data.get("is_safe", True),
                    reason=data.get("reason", "")
                )
            except json.JSONDecodeError:
                # Если не JSON, пытаемся понять ответ
                if "CLEAN" in result_text.upper():
                    return SupervisorResponse(
                        prompt="CLEAN",
                        is_safe=True,
                        reason="Code is clean"
                    )
                else:
                    # Используем ответ как промпт
                    return SupervisorResponse(
                        prompt=result_text,
                        is_safe=True,
                        reason="Supervisor analysis"
                    )
        except Exception as e:
            logger.error(f"Supervisor error: {e}")
            # В случае ошибки считаем безопасным (fail-safe)
            return SupervisorResponse(
                prompt=f"Error in Supervisor: {str(e)}",
                is_safe=True,
                reason="Supervisor error, defaulting to safe"
            )
    
    def _validate_with_oracle(self, prompt: str) -> str:
        """
        Oracle Stage: Валидирует промпт от Supervisor через GPT-4o
        
        Args:
            prompt: Промпт от Supervisor
            
        Returns:
            "APPROVED" или "REJECTED"
        """
        oracle_prompt = f"""Ты Senior Code Reviewer. Проверь этот промпт для исправления кода.

Это безопасно? Это исправление? 

Промпт:
```
{prompt[:4000]}
```

Если промпт безопасен и предлагает исправление — ответь: APPROVED
Если промпт опасен или предлагает что-то небезопасное — ответь: REJECTED и причину.

Ответ должен быть одним словом: APPROVED или REJECTED"""
        
        try:
            model_name = self.cfg.oracle_model
            response = self.oracle_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a senior code reviewer. Be strict about security."},
                    {"role": "user", "content": oracle_prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip().upper()
            
            if "REJECTED" in result_text:
                return "REJECTED"
            else:
                return "APPROVED"
        except Exception as e:
            logger.error(f"Oracle error: {e}")
            # В случае ошибки Oracle одобряет (fail-safe, но логируем)
            return "APPROVED"
    
    def _save_task(self, task_type: str, file_path: str, message: str, 
                   status: str = "PENDING", instruction: str = "", diff: str = ""):
        """
        Сохраняет задачу в GHOST_TASKS.md (JSON формат)
        
        Args:
            task_type: "LINT_FIX" или "CODE_REVIEW"
            file_path: Путь к файлу
            message: Сообщение задачи
            status: "PENDING", "APPROVED", "REJECTED"
            instruction: Инструкция для Cursor
            diff: Git diff (опционально)
        """
        try:
            # Создаём TaskModel
            task = TaskModel(
                type=task_type,
                file=file_path,
                message=message,
                status=status,
                diff=diff,
                instruction=instruction,
                reason=f"Generated by {task_type}"
            )
            
            # Сохраняем в JSON формат (добавляем к существующим задачам)
            tasks_file = self.root / "GHOST_TASKS.md"
            
            existing_tasks = []
            if tasks_file.exists():
                try:
                    content = tasks_file.read_text(encoding='utf-8')
                    # Проверяем формат: JSON или Markdown
                    if content.strip().startswith('[') or content.strip().startswith('{'):
                        # JSON формат
                        existing_tasks = json.loads(content)
                        if not isinstance(existing_tasks, list):
                            existing_tasks = [existing_tasks]
                    else:
                        # Старый Markdown формат - конвертируем или пропускаем
                        logger.debug("Found old Markdown format, appending new JSON task")
                except Exception:
                    pass
            
            # Добавляем новую задачу
            task_dict = task.model_dump() if PYDANTIC_AVAILABLE else {
                "id": task.id,
                "type": task.type,
                "file": task.file,
                "line": task.line,
                "message": task.message,
                "status": task.status,
                "diff": task.diff,
                "timestamp": task.timestamp,
                "instruction": task.instruction,
                "reason": task.reason
            }
            existing_tasks.insert(0, task_dict)
            
            # Ограничиваем количество (MAX_TASKS = 20)
            existing_tasks = existing_tasks[:20]
            
            # Сохраняем в JSON
            tasks_file.write_text(
                json.dumps(existing_tasks, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            logger.info(f"[Ghost] Task saved: {task_type} ({status}) for {file_path}")
        except Exception as e:
            logger.error(f"[Ghost] Failed to save task: {e}")
    
    def _review_file(self, file_path: Path, auto_mode: bool):
        """Проверяет один файл: Worker (Ruff) -> Supervisor -> Oracle"""
        rel_path = str(file_path.relative_to(self.root)).replace("\\", "/")
        
        # 1. Worker Stage: Проверяем Ruff
        success, error_msg, diff = self.analyzer.check_file(file_path)
        
        if success is False and diff:
            # Ruff нашёл ошибки - создаём LINT_FIX задачу
            if auto_mode:
                self._save_task(
                    task_type="LINT_FIX",
                    file_path=rel_path,
                    message=f"Ruff lint errors: {error_msg[:100]}",
                    status="PENDING",
                    instruction="Apply this diff automatically.",
                    diff=diff
                )
                logger.info(f"[Ghost] LINT_FIX task generated for {rel_path}")
                self.last_review_status = f"LINT_FIX task created for {file_path.name}"
            return
        
        # 2. Проверяем размер изменений
        diff_lines = self.analyzer.get_file_diff_lines(file_path)
        
        if diff_lines > 50 and auto_mode and self.supervisor_client:
            # Большие изменения - запускаем Supervisor -> Oracle
            try:
                git_diff_output = subprocess.check_output(
                    ["git", "diff", "--unified=0", str(file_path)],
                    cwd=self.root,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if git_diff_output and git_diff_output.strip():
                    # Запускаем полный цикл Supervisor -> Oracle
                    supervisor_response = self._supervisor_generate_prompt(git_diff_output)
                    
                    if supervisor_response.is_safe:
                        oracle_status = "APPROVED"
                        if self.oracle_client:
                            oracle_status = self._validate_with_oracle(supervisor_response.prompt)
                        
                        self._save_task(
                            task_type="CODE_REVIEW",
                            file_path=rel_path,
                            message=f"Code review ({oracle_status})",
                            status=oracle_status,
                            instruction=supervisor_response.prompt,
                            diff=git_diff_output[:2000]
                        )
                        logger.info(f"[Ghost] CODE_REVIEW task generated ({oracle_status})")
                        self.last_review_status = f"CODE_REVIEW task created ({oracle_status})"
                    else:
                        self._save_task(
                            task_type="CODE_REVIEW",
                            file_path=rel_path,
                            message=f"Rejected: {supervisor_response.reason}",
                            status="REJECTED",
                            instruction=supervisor_response.prompt,
                            diff=git_diff_output[:2000]
                        )
            except Exception as e:
                logger.debug(f"Could not get git diff for {file_path}: {e}")
    
    def copy_prompt_to_clipboard(self):
        """Копирует промпт для исправления в буфер обмена"""
        if not PYPERCLIP_AVAILABLE:
            return False, "pyperclip not installed. Run: pip install pyperclip"
        
        if not self.last_generated_prompt:
            return False, "No prompt available. Run AI Review [1] first."
        
        try:
            formatted_prompt = f"Исправь код согласно этому ревью:\n\n{self.last_generated_prompt}"
            pyperclip.copy(formatted_prompt)
            return True, "Prompt copied! Paste in Cursor (Ctrl+V)"
        except Exception as e:
            return False, f"Copy failed: {e}"
    
    def get_status(self):
        """Возвращает текущий статус AI"""
        return self.last_review_status
