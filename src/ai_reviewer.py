"""
AIReviewer — AI Code Review через Google Gemini

Использует:
1. Глобальный конфиг (~/.ghost/config.json) — приоритет
2. Локальный конфиг (ghost_config.json) — fallback
"""

import subprocess
from pathlib import Path
from .config import Config
from .core import logger

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


class AIReviewer:
    def __init__(self, root: Path):
        self.root = root
        self.cfg = Config.get()
        self.last_generated_prompt = ""
        self.client = None
        self.provider = "gemini"
        self.model = "gemini-2.0-flash"
        
        # Получаем API ключ (приоритет: глобальный конфиг > локальный конфиг)
        api_key = self._get_api_key()
        
        if not api_key:
            self.last_review_status = "AI: Run 'ghost --setup' to configure"
            return
        
        if not GENAI_AVAILABLE:
            self.last_review_status = "AI: Install google-genai (pip install google-genai)"
            logger.warning("google-genai not installed. AI Review disabled.")
            return

        try:
            # Новый API: создаём Client
            self.client = genai.Client(api_key=api_key)
            self.last_review_status = "AI Ready"
            logger.info("AI Reviewer initialized successfully")
        except Exception as e:
            self.last_review_status = f"AI Init Error: {str(e)[:50]}"
            logger.error(f"AI Init failed: {e}")
    
    def _get_api_key(self) -> str:
        """Получает API ключ из глобального или локального конфига"""
        # 1. Пробуем глобальный конфиг
        try:
            from .global_config import GlobalConfig
            global_cfg = GlobalConfig.get()
            if global_cfg.api_key:
                self.provider = global_cfg.provider
                self.model = global_cfg.model
                logger.debug(f"Using API key from global config ({global_cfg.config_location})")
                return global_cfg.api_key
        except Exception as e:
            logger.debug(f"Global config not available: {e}")
        
        # 2. Fallback на локальный конфиг
        if self.cfg.ai_api_key:
            logger.debug("Using API key from local ghost_config.json")
            return self.cfg.ai_api_key
        
        return ""

    def run_review(self):
        """Запускает AI Review на git diff"""
        if not self.client:
            return 
        
        if "Error" in self.last_review_status:
            return

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
            except subprocess.CalledProcessError:
                self.last_review_status = "AI: No git changes detected"
                return
            except FileNotFoundError:
                self.last_review_status = "AI: Git not found"
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

        # Формируем промпт для AI
        review_prompt = f"""Ты Senior Code Reviewer. Проанализируй этот Git Diff.

Найди:
1. Ошибки безопасности (SQL injection, XSS, hardcoded secrets)
2. Дублирование кода
3. Нарушения PEP8/стиля
4. Потенциальные баги

Если есть критические ошибки — напиши ПРОМПТ для Cursor AI, чтобы он исправил эти ошибки.
Включи конкретные имена файлов и строк.

Если ошибок нет или они косметические — ответь одним словом: CLEAN

Git Diff:
```
{output[:8000]}
```"""

        # Отправляем в Gemini
        try:
            # Используем модель из конфига
            response = self.client.models.generate_content(
                model=self.model,
                contents=review_prompt
            )
            result_text = response.text.strip()
            
            if "CLEAN" in result_text.upper():
                self.last_review_status = "AI: Code is clean [OK]"
                self.last_generated_prompt = ""
            else:
                self.last_review_status = "AI: Issues found! Press [2] to copy fix"
                self.last_generated_prompt = result_text
                logger.info("AI Review completed with issues found")
                
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                self.last_review_status = "AI: Quota exceeded. Wait 1 min."
            elif "401" in error_msg or "403" in error_msg:
                self.last_review_status = "AI: Invalid API key"
            else:
                self.last_review_status = f"AI Error: {str(e)[:40]}"
            logger.error(f"AI Review failed: {e}")

    def copy_prompt_to_clipboard(self):
        """Копирует промпт для исправления в буфер обмена"""
        if not PYPERCLIP_AVAILABLE:
            return False, "pyperclip not installed. Run: pip install pyperclip"
        
        if not self.last_generated_prompt:
            return False, "No prompt available. Run AI Review [1] first."
        
        try:
            # Форматируем промпт для Cursor
            formatted_prompt = f"Исправь код согласно этому ревью:\n\n{self.last_generated_prompt}"
            pyperclip.copy(formatted_prompt)
            return True, "Prompt copied! Paste in Cursor (Ctrl+V)"
        except Exception as e:
            return False, f"Copy failed: {e}"

    def get_status(self):
        """Возвращает текущий статус AI"""
        return self.last_review_status
