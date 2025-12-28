import subprocess
import pyperclip
import google.generativeai as genai
from pathlib import Path
from .config import Config
from .core import logger

class AIReviewer:
    def __init__(self, root: Path):
        self.root = root
        self.cfg = Config.get()
        
        genai.configure(api_key=self.cfg.ai_api_key)
        
        self.client = genai.GenerativeModel(self.cfg.ai_model)
        
        self.last_generated_prompt = ""
        self.last_review_status = "Idle"

    def run_review(self):
        self.last_review_status = "Analyzing diff..."
        
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
            response = self.client.generate_content(review_prompt)
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
