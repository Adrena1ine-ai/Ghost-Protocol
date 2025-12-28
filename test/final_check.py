"""
Автоматическая финальная проверка Ghost Protocol
Проверяет основные функции без интерактивного ввода
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_test(name, result, details=""):
    status = "[OK]" if result else "[FAIL]"
    print(f"{status} {name}")
    if details:
        print(f"    {details}")

def test_analyzer_complexity():
    """Тест: Radon проверяет подпапки рекурсивно"""
    print_header("TEST 1: Radon Complexity (Recursive)")
    
    try:
        # Импортируем модуль
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.config import Config
        from src.analyzer import CodeAnalyzer
        
        # Создаём временный проект с кодом в подпапке
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            Config.init(root)
            
            # Создаём подпапку с кодом высокой сложности
            test_dir = root / "test_code"
            test_dir.mkdir()
            
            # Создаём файл с высокой сложностью
            complex_file = test_dir / "complex.py"
            complex_file.write_text("""def complex_func(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                if x + y > 10:
                    if x + z > 10:
                        return "very complex"
    return "simple"
""")
            
            analyzer = CodeAnalyzer(root)
            comp_ok, comp_msg = analyzer.analyze_complexity()
            
            # Проверяем, что Radon нашёл сложность
            if comp_ok is False:
                print_test("Radon found complexity in subfolder", True, comp_msg)
                return True
            else:
                print_test("Radon found complexity in subfolder", False, f"Expected to find complexity, got: {comp_msg}")
                return False
                
    except Exception as e:
        print_test("Radon Complexity Test", False, f"Error: {e}")
        return False

def test_ai_reviewer_git_diff():
    """Тест: AI Reviewer использует git diff --cached"""
    print_header("TEST 2: AI Reviewer Git Diff (--cached)")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.config import Config
        from src.ai_reviewer import AIReviewer
        
        # Проверяем код метода run_review
        import inspect
        source = inspect.getsource(AIReviewer.run_review)
        
        if "--cached" in source:
            print_test("AI Reviewer uses --cached flag", True, "Found '--cached' in run_review method")
            return True
        else:
            print_test("AI Reviewer uses --cached flag", False, "Could not find '--cached' in code")
            return False
            
    except Exception as e:
        print_test("AI Reviewer Git Diff Test", False, f"Error: {e}")
        return False

def test_file_classification():
    """Тест: File Classification работает"""
    print_header("TEST 3: File Classification")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.config import Config
        from src.classifier import FileClassifier
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            Config.init(root)
            
            classifier = FileClassifier(root)
            
            # Тест 1: JUNK файл
            junk_file = root / "FULL_PROJECT_CODE.txt"
            junk_file.write_text("test")
            action = classifier.classify(junk_file)
            test1 = (action == "JUNK")
            print_test("JUNK pattern detection", test1, f"Action: {action}")
            
            # Тест 2: Большой .txt файл
            large_txt = root / "large.txt"
            large_txt.write_bytes(b"X" * (60 * 1024))  # 60KB
            action = classifier.classify(large_txt)
            test2 = (action == "JUNK")
            print_test("Large .txt file detection", test2, f"Action: {action}, Size: {large_txt.stat().st_size/1024:.1f}KB")
            
            # Тест 3: TRASH файл
            trash_file = root / "dump_backup.sql"
            trash_file.write_bytes(b"X" * (3 * 1024 * 1024))  # 3MB
            action = classifier.classify(trash_file)
            test3 = (action == "TRASH")
            print_test("TRASH file detection", test3, f"Action: {action}, Size: {trash_file.stat().st_size/(1024*1024):.1f}MB")
            
            return test1 and test2 and test3
            
    except Exception as e:
        print_test("File Classification", False, f"Error: {e}")
        return False

def test_ignore_manager():
    """Тест: Ignore Manager работает"""
    print_header("TEST 4: Ignore Manager")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.config import Config
        from src.ignore_manager import IgnoreFileManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            Config.init(root)
            
            ignore_mgr = IgnoreFileManager(root)
            
            # Проверяем, что файлы созданы
            gitignore = root / ".gitignore"
            cursorignore = root / ".cursorignore"
            
            test1 = gitignore.exists()
            test2 = cursorignore.exists()
            print_test(".gitignore created", test1)
            print_test(".cursorignore created", test2)
            
            # Тест добавления
            ignore_mgr.add_junk({"test_file.txt"})
            
            gitignore_content = gitignore.read_text()
            cursorignore_content = cursorignore.read_text()
            
            test3 = "test_file.txt" in gitignore_content
            test4 = "test_file.txt" in cursorignore_content
            print_test("JUNK added to .gitignore", test3)
            print_test("JUNK added to .cursorignore", test4)
            
            return test1 and test2 and test3 and test4
            
    except Exception as e:
        print_test("Ignore Manager", False, f"Error: {e}")
        return False

def test_config():
    """Тест: Config работает"""
    print_header("TEST 5: Config System")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.config import Config
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            Config.init(root)
            cfg = Config.get()
            
            # Проверяем основные свойства
            test1 = hasattr(cfg, 'data_min_size_kb')
            test2 = cfg.data_min_size_kb == 100
            test3 = hasattr(cfg, 'code_folders')
            test4 = hasattr(cfg, 'junk_folders')
            
            print_test("data_min_size_kb property exists", test1, f"Value: {cfg.data_min_size_kb if test1 else 'N/A'}")
            print_test("data_min_size_kb default value", test2)
            print_test("code_folders property exists", test3)
            print_test("junk_folders property exists", test4)
            
            return test1 and test2 and test3 and test4
            
    except Exception as e:
        print_test("Config System", False, f"Error: {e}")
        return False

def cleanup_test_files():
    """Очистка тестовых файлов"""
    print_header("CLEANUP: Removing test files")
    
    test_project = Path("C:/MuJIa v7 test 1")
    if not test_project.exists():
        print("[SKIP] Test project not found")
        return
    
    test_files = [
        "dummy.txt",
        "test_large.txt",
        "test_data.csv",
        "test_data_large.csv",
        "FULL_PROJECT_CODE.txt",
        "dump_backup.sql"
    ]
    
    cleaned = 0
    for fname in test_files:
        fpath = test_project / fname
        if fpath.exists():
            try:
                fpath.unlink()
                cleaned += 1
            except Exception:
                pass
    
    # Очистка test_code_review
    test_dir = test_project / "test_code_review"
    if test_dir.exists():
        try:
            import shutil
            shutil.rmtree(test_dir)
            cleaned += 1
        except Exception:
            pass
    
    print(f"[OK] Cleaned {cleaned} test files/directories")

def main():
    print_header("GHOST PROTOCOL FINAL AUTOMATED TESTS")
    
    results = []
    
    # Запускаем тесты
    results.append(("Radon Complexity", test_analyzer_complexity()))
    results.append(("AI Reviewer Git Diff", test_ai_reviewer_git_diff()))
    results.append(("File Classification", test_file_classification()))
    results.append(("Ignore Manager", test_ignore_manager()))
    results.append(("Config System", test_config()))
    
    # Итоги
    print_header("TEST RESULTS SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")
    
    # Очистка
    cleanup_test_files()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

