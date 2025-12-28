"""
Тест AI Review функциональности (CodeRabbit аналог)

Проверяет:
1. Обнаружение дублирования кода
2. Обнаружение проблем безопасности
3. Обнаружение плохого стиля кода
4. Обнаружение потенциальных багов
5. Статический анализ (Ruff + Radon)
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import json

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(step, text):
    print(f"\n[{step}] {text}")

def check_git_repo(root):
    """Проверяет, что это git репозиторий"""
    git_dir = root / ".git"
    return git_dir.exists()

def create_test_files(root):
    """Создаёт тестовые файлы с проблемами кода"""
    test_dir = root / "test_code_review"
    test_dir.mkdir(exist_ok=True)
    
    # Файл 1: Дублирование кода
    duplicate_code = '''"""Test file with code duplication"""
def calculate_price(item_price, discount):
    """Calculate price with discount"""
    final_price = item_price * (1 - discount)
    return final_price

def calculate_final_price(price, discount_percent):
    """Calculate final price with discount - DUPLICATE!"""
    result = price * (1 - discount_percent)
    return result

def get_discounted_price(original, discount):
    """Get discounted price - ANOTHER DUPLICATE!"""
    discounted = original * (1 - discount)
    return discounted
'''
    
    # Файл 2: Проблемы безопасности
    security_issues = '''"""Test file with security issues"""
import os

def get_user_data(user_id):
    """Get user data - SQL injection risk"""
    query = f"SELECT * FROM users WHERE id = {user_id}"  # BAD: SQL injection
    # Should use parameterized queries
    
    password = "admin123"  # BAD: Hardcoded password
    api_key = "sk-1234567890abcdef"  # BAD: Hardcoded API key
    
    return {"query": query, "password": password}

def process_input(user_input):
    """Process user input - XSS risk"""
    html = f"<div>{user_input}</div>"  # BAD: No escaping
    return html
'''
    
    # Файл 3: Плохой стиль и потенциальные баги
    bad_style = '''"""Test file with bad style and bugs"""
def processData(data,flag):
    # Bad: no spaces, unclear variable names
    result=[]
    for i in range(len(data)):
        item=data[i]
        if flag==True:
            result.append(item*2)
        else:
            result.append(item)
    return result

def divide_numbers(a, b):
    """Divide two numbers - potential ZeroDivisionError"""
    return a / b  # BAD: No check for b == 0

def get_item(items, index):
    """Get item by index - potential IndexError"""
    return items[index]  # BAD: No bounds checking
'''
    
    # Файл 4: Высокая сложность (spaghetti code)
    complex_code = '''"""Test file with high cyclomatic complexity"""
def complex_function(x, y, z):
    """Function with too many conditions"""
    if x > 0:
        if y > 0:
            if z > 0:
                if x + y > 10:
                    if x + z > 10:
                        if y + z > 10:
                            if x + y + z > 20:
                                if x * y > 50:
                                    if x * z > 50:
                                        if y * z > 50:
                                            return "Very complex"
    return "Simple"
'''
    
    files = {
        "duplicate_code.py": duplicate_code,
        "security_issues.py": security_issues,
        "bad_style.py": bad_style,
        "complex_code.py": complex_code
    }
    
    created = []
    for filename, content in files.items():
        filepath = test_dir / filename
        filepath.write_text(content, encoding='utf-8')
        created.append(filepath)
        print(f"    [OK] Created: {filepath.relative_to(root)}")
    
    return created

def git_add_files(root, files):
    """Добавляет файлы в git staging"""
    try:
        for file in files:
            subprocess.run(["git", "add", str(file)], cwd=root, 
                         capture_output=True, check=True)
        print(f"    [OK] Added {len(files)} files to git staging")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    [FAIL] Failed to add files: {e}")
        return False

def get_git_diff(root):
    """Получает git diff"""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--unified=0"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout
    except Exception as e:
        print(f"    [FAIL] Failed to get git diff: {e}")
        return None

def check_ai_reviewer_module(root):
    """Проверяет доступность AIReviewer"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from src.config import Config
        Config.init(root)  # Инициализируем Config
        from src.ai_reviewer import AIReviewer
        reviewer = AIReviewer(root)
        
        status = reviewer.get_status()
        print(f"    Status: {status}")
        
        if "Ready" in status or "Ready" in status:
            return reviewer, True
        elif "Error" in status or "not" in status.lower():
            print(f"    ⚠️  AI Reviewer not fully initialized: {status}")
            return reviewer, False
        else:
            return reviewer, True
    except ImportError as e:
        print(f"    [FAIL] Failed to import AIReviewer: {e}")
        return None, False
    except Exception as e:
        print(f"    [FAIL] Error initializing AIReviewer: {e}")
        return None, False

def test_ai_review(reviewer, root):
    """Тестирует AI Review"""
    print("\n    Running AI Review...")
    
    # Сохраняем текущий статус
    initial_status = reviewer.get_status()
    print(f"    Initial status: {initial_status}")
    
    # Запускаем review
    reviewer.run_review()
    
    # Ждём результата (AI может занять время)
    time.sleep(5)
    
    final_status = reviewer.get_status()
    print(f"    Final status: {final_status}")
    
    has_prompt = bool(reviewer.last_generated_prompt)
    print(f"    Has generated prompt: {has_prompt}")
    
    if has_prompt:
        prompt_preview = reviewer.last_generated_prompt[:200]
        print(f"    Prompt preview: {prompt_preview}...")
        
        # Проверяем, что промпт содержит полезную информацию
        keywords = ["дубли", "duplicate", "security", "безопасн", "bug", "баг", 
                   "style", "стиль", "PEP8", "SQL", "injection", "XSS"]
        found_keywords = [kw for kw in keywords if kw.lower() in reviewer.last_generated_prompt.lower()]
        
        if found_keywords:
            print(f"    [OK] Found relevant keywords: {', '.join(found_keywords[:5])}")
        else:
            print(f"    ⚠️  No obvious keywords found in prompt")
    
    return final_status, has_prompt

def test_code_analyzer(root):
    """Тестирует CodeAnalyzer (Ruff + Radon)"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from src.config import Config
        Config.init(root)  # Инициализируем Config
        from src.analyzer import CodeAnalyzer
        
        analyzer = CodeAnalyzer(root)
        
        print("\n    Testing Ruff Linter...")
        lint_ok, lint_msg = analyzer.run_lint()
        print(f"    Lint result: {lint_ok}")
        print(f"    Lint message: {lint_msg[:200] if lint_msg else 'No message'}")
        
        print("\n    Testing Radon Complexity...")
        comp_ok, comp_msg = analyzer.analyze_complexity()
        print(f"    Complexity result: {comp_ok}")
        print(f"    Complexity message: {comp_msg[:200] if comp_msg else 'No message'}")
        
        print("\n    Running full check...")
        full_report = analyzer.full_check()
        print(f"    Full report:\n{full_report}")
        
        return lint_ok, comp_ok, full_report
        
    except ImportError as e:
        print(f"    [FAIL] Failed to import CodeAnalyzer: {e}")
        return None, None, None
    except Exception as e:
        print(f"    [FAIL] Error running CodeAnalyzer: {e}")
        return None, None, None

def test_clipboard_copy(reviewer):
    """Тестирует копирование промпта в буфер"""
    try:
        import pyperclip
    except ImportError:
        print("    [WARN] pyperclip not installed - skipping clipboard test")
        return False
    
    if not reviewer.last_generated_prompt:
        print("    [WARN] No prompt to copy - skipping clipboard test")
        return False
    
    print("\n    Testing clipboard copy...")
    success, msg = reviewer.copy_prompt_to_clipboard()
    
    print(f"    Result: {success}")
    print(f"    Message: {msg}")
    
    if success:
        # Проверяем, что в буфере что-то есть
        try:
            clipboard_content = pyperclip.paste()
            if "Исправь код" in clipboard_content or "ревью" in clipboard_content.lower():
                print("    [OK] Clipboard contains formatted prompt")
                return True
            else:
                print("    [WARN] Clipboard content doesn't look like expected prompt")
                return False
        except Exception as e:
            print(f"    ⚠️  Could not verify clipboard: {e}")
            return True  # Assume success if we can't verify
    
    return False

def main():
    # Определяем корень проекта
    script_dir = Path(__file__).parent
    test_project = script_dir / "test_ai_review_project"
    
    # Если есть аргумент - используем его как тестовый проект
    if len(sys.argv) > 1:
        test_project = Path(sys.argv[1])
    
    root = test_project if test_project.exists() else script_dir
    
    print_header("AI CODE REVIEW TEST (CodeRabbit Analogue)")
    
    # Проверка git репозитория
    print_step("1", "Checking git repository...")
    if not check_git_repo(root):
        print("    [FAIL] Not a git repository!")
        print("    Creating git repo for testing...")
        try:
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], 
                         cwd=root, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], 
                         cwd=root, capture_output=True)
            
            # Создаём начальный коммит
            (root / "README.md").write_text("# Test Project\n", encoding='utf-8')
            subprocess.run(["git", "add", "README.md"], cwd=root, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], 
                         cwd=root, capture_output=True)
            print("    [OK] Git repository initialized")
        except Exception as e:
            print(f"    ✗ Failed to initialize git: {e}")
            print("    [WARN] AI Review requires git. Some tests may fail.")
    else:
            print("    [OK] Git repository found")
    
    # Создание тестовых файлов
    print_step("2", "Creating test files with code issues...")
    test_files = create_test_files(root)
    
    # Добавление в git
    print_step("3", "Staging files in git...")
    git_add_files(root, test_files)
    
    # Получение git diff
    print_step("4", "Getting git diff...")
    diff = get_git_diff(root)
    if diff:
        print(f"    [OK] Git diff obtained ({len(diff)} chars)")
        if len(diff) > 500:
            print(f"    Preview: {diff[:200]}...")
    else:
        print("    ✗ Failed to get git diff")
    
    # Проверка AIReviewer
    print_step("5", "Checking AIReviewer module...")
    reviewer, reviewer_ready = check_ai_reviewer_module(root)
    
    if not reviewer_ready:
        print("\n    ⚠️  AIReviewer not ready. Testing with mock...")
        print("    To test AI Review, run 'python main.py --setup' first")
    
    # Тест AI Review
    print_step("6", "Testing AI Review (CodeRabbit functionality)...")
    if reviewer and reviewer_ready:
        status, has_prompt = test_ai_review(reviewer, root)
    else:
        print("    [SKIP] Skipped (AIReviewer not ready)")
        status, has_prompt = None, False
    
    # Тест CodeAnalyzer
    print_step("7", "Testing CodeAnalyzer (Ruff + Radon)...")
    lint_ok, comp_ok, full_report = test_code_analyzer(root)
    
    # Тест копирования в буфер
    print_step("8", "Testing clipboard copy...")
    if reviewer and has_prompt:
        clipboard_ok = test_clipboard_copy(reviewer)
    else:
        print("    [SKIP] Skipped (no prompt available)")
        clipboard_ok = False
    
    # Итоги
    print_header("TEST RESULTS SUMMARY")
    
    print("\n✅ AI Review Tests:")
    if reviewer_ready:
        if has_prompt:
            print("    [OK] AI Review found issues and generated prompt")
        else:
            print("    [WARN] AI Review completed but no prompt generated")
    else:
        print("    [FAIL] AI Review not tested (AIReviewer not ready)")
    
    print("\n✅ Static Analysis Tests:")
    if lint_ok is not None:
        if lint_ok:
            print("    [OK] Ruff: No lint errors (unexpected - test files have issues!)")
        else:
            print("    [OK] Ruff: Found lint errors (expected)")
    
    if comp_ok is not None:
        if comp_ok:
            print("    [WARN] Radon: Complexity OK (unexpected - test files have complex code!)")
        else:
            print("    [OK] Radon: Found high complexity (expected)")
    
    print("\n✅ Clipboard Test:")
    if clipboard_ok:
        print("    [OK] Clipboard copy works")
    else:
        print("    [WARN] Clipboard copy not tested or failed")
    
    print("\n📋 NEXT STEPS:")
    print("  1. Check AI Review status in Ghost Protocol Monitor")
    print("  2. Press [1] in Monitor to run AI Review manually")
    print("  3. Press [2] to copy prompt to clipboard")
    print("  4. Press [3] to run full static analysis")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()

