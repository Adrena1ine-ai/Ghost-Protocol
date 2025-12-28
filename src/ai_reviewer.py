import subprocess
import pyperclip
from pathlib import Path
from .config import Config
from .core import logger

# Пробуем импортировать новую библиотеку, если не получается - используем старую
try:
    import google.genai as genai
    USE_NEW_API = True
except ImportError:
    try:
        import google.generativeai as genai
        USE_NEW_API = False
    except ImportError:
        genai = None
        USE_NEW_API = False

class AIReviewer:
    def __init__(self, root: Path):
        self.root = root
        self.cfg = Config.get()
        
        if genai is None:
            logger.warning("Neither google-genai nor google-generativeai is installed. AI Review will not work.")
            self.model = None
            self.client = None
        else:
            # Инициализация API
            try:
                if USE_NEW_API:
                    # Новый API (google-genai) - если доступен
                    self.client = genai.Client(api_key=self.cfg.ai_api_key)
                    self.model = self.client.models.get(self.cfg.ai_model) if hasattr(self.client, 'models') else None
                else:
                    # Старый API (google-generativeai)
                    genai.configure(api_key=self.cfg.ai_api_key)
                    self.model = genai.GenerativeModel(self.cfg.ai_model)
                    self.client = None
            except Exception as e:
                logger.warning(f"Failed to initialize AI client: {e}")
                self.model = None
                self.client = None
        
        self.last_generated_prompt = ""
        self.last_review_status = "Idle"

    def run_review(self):
        """Запускает ревью изменений (git diff) и генерирует промпт для исправления."""
        if self.model is None:
            self.last_review_status = "AI client not initialized. Check API key or install google-genai."
            return
            
        self.last_review_status = "Analyzing diff..."
        
        # Получаем diff
        try:
            output = subprocess.check_output(
                ["git", "diff", "HEAD", "--unified=0"],
                cwd=self.root,
                stderr=subprocess.PIPE,
                text=True,
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

        # Промпт для LLM
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
                # Новый API стиль
                response = self.model.generate(prompt=review_prompt)
                if hasattr(response, 'text'):
                    result_text = response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    result_text = response.candidates[0].content.parts[0].text.strip()
                else:
                    result_text = str(response).strip()
            else:
                # Старый API стиль (google-generativeai)
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
        """Копирует последний сгенерированный промпт в буфер обмена."""
        if not self.last_generated_prompt:
            return False, "No prompt available. Run AI Review first."
        
        try:
            pyperclip.copy(self.last_generated_prompt)
            return True, "Prompt copied to clipboard!"
        except Exception as e:
            return False, f"Failed to copy: {e}"

    def get_status(self):
        return self.last_review_status
