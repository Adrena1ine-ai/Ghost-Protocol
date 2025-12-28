import subprocess
import pyperclip
from pathlib import Path
from .config import Config
from .core import logger

# Пробуем импортировать новую библиотеку google-genai
try:
    from google.genai import Client as GenAIClient
    USE_NEW_API = True
except ImportError:
    # Fallback на старую библиотеку, если новая не установлена
    try:
        import google.generativeai as genai
        USE_NEW_API = False
    except ImportError:
        GenAIClient = None
        genai = None
        USE_NEW_API = False
        logger.warning("Neither google-genai nor google-generativeai is installed. AI Review will not work.")

class AIReviewer:
    def __init__(self, root: Path):
        self.root = root
        self.cfg = Config.get()
        self.last_generated_prompt = ""
        self.last_review_status = "Checking API Key..."
        self.client = None
        self.model = None

        # Проверка ключа
        if not self.cfg.ai_api_key or self.cfg.ai_api_key.strip() == "":
            self.last_review_status = "Error: API Key is empty. Check ghost_config.json."
            logger.warning("AI API Key is empty. AI Review will not work.")
            return

        # Инициализация клиента
        try:
            if USE_NEW_API and GenAIClient:
                # Новый API (google-genai)
                self.client = GenAIClient(api_key=self.cfg.ai_api_key)
                self.model = self.cfg.ai_model
                self.last_review_status = "AI Ready (google-genai)"
            elif not USE_NEW_API and genai:
                # Старый API (google-generativeai)
                genai.configure(api_key=self.cfg.ai_api_key)
                self.model = genai.GenerativeModel(self.cfg.ai_model)
                self.last_review_status = "AI Ready (google-generativeai)"
            else:
                self.last_review_status = "Error: No AI library available."
        except Exception as e:
            self.last_review_status = f"Init Error: {e}"
            logger.error(f"AI Init failed: {e}")

    def run_review(self):
        """Запускает ревью изменений (git diff) и генерирует промпт для исправления."""
        if "Error" in self.last_review_status or not self.client and not self.model:
            return # Не запускаем, если ошибка инициализации

        self.last_review_status = "Analyzing diff..."
        
        try:
            output = subprocess.check_output(
                ["git", "diff", "HEAD", "--unified=0"],
                cwd=self.root,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',  # Заменяем нечитаемые символы вместо краша
                timeout=10
            )
        except subprocess.CalledProcessError:
            self.last_review_status = "No changes detected."
            return
        except Exception as e:
            self.last_review_status = f"Error getting diff: {e}"
            return

        if not output:
            self.last_review_status = "No changes detected."
            return

        review_prompt = f"""
        Ты Senior Code Reviewer. Проанализируй этот Git Diff.
        Найди ошибки безопасности, дублирование кода, нарушения PEP8.
        
        Если есть критические ошибки — напиши подробный ПРОМПТ для Cursor (или другого AI),
        чтобы он исправил эти ошибки. Включи в промпт конкретные имена файлов и строк.
        
        Если ошибок нет или они косметические — ответь просто "CLEAN".
        
        Git Diff:
        {output}
        """

        try:
            if USE_NEW_API and self.client:
                # Новый API (google-genai)
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[review_prompt]
                )
                # Извлекаем текст из ответа
                if hasattr(response, 'text'):
                    result_text = response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    if hasattr(response.candidates[0], 'content'):
                        if hasattr(response.candidates[0].content, 'parts'):
                            result_text = response.candidates[0].content.parts[0].text.strip()
                        else:
                            result_text = str(response.candidates[0].content).strip()
                    else:
                        result_text = str(response.candidates[0]).strip()
                else:
                    result_text = str(response).strip()
            else:
                # Старый API (google-generativeai)
                response = self.model.generate_content(review_prompt)
                result_text = response.text.strip()
            
            if "CLEAN" in result_text.upper():
                self.last_review_status = "Review: ✅ Code is clean"
                self.last_generated_prompt = ""
            else:
                self.last_review_status = "Review: ⚠️ Issues found. Prompt generated."
                self.last_generated_prompt = result_text
                
        except Exception as e:
            self.last_review_status = f"Review Error: {e}"
            logger.error(f"AI Review failed: {e}")

    def copy_prompt_to_clipboard(self):
        if not self.last_generated_prompt:
            return False, "No prompt available. Run AI Review first."
        
        try:
            pyperclip.copy(self.last_generated_prompt)
            return True, "Prompt copied to clipboard!"
        except Exception as e:
            return False, f"Failed to copy: {e}"

    def get_status(self):
        return self.last_review_status
