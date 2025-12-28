"""
Тестовый скрипт для проверки работы Ghost Protocol

Проверяет:
1. Классификацию файлов (JUNK, DATA, TRASH, CODE, UNKNOWN)
2. Добавление в игнор-файлы
3. Перемещение в _trash
4. Логирование событий
"""

import os
import time
import subprocess
from pathlib import Path
import json

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(step, text):
    print(f"\n[{step}] {text}")

def create_test_file(filepath, size_kb=1, content=None):
    """Создаёт тестовый файл заданного размера"""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if content:
        filepath.write_text(content, encoding='utf-8')
    else:
        # Создаём файл нужного размера (примерно)
        chunk = "X" * 1024  # 1KB chunk
        with open(filepath, 'w', encoding='utf-8') as f:
            for _ in range(size_kb):
                f.write(chunk)
    
    print(f"    ✓ Created: {filepath} ({filepath.stat().st_size / 1024:.1f} KB)")

def check_ignore_files(root, file_paths):
    """Проверяет, добавлены ли файлы в игнор-файлы"""
    gitignore = root / ".gitignore"
    cursorignore = root / ".cursorignore"
    
    results = {
        "gitignore": [],
        "cursorignore": [],
        "both": [],
        "none": []
    }
    
    gitignore_content = gitignore.read_text(encoding='utf-8') if gitignore.exists() else ""
    cursorignore_content = cursorignore.read_text(encoding='utf-8') if cursorignore.exists() else ""
    
    for file_path in file_paths:
        rel_path = str(file_path).replace("\\", "/")
        file_name = Path(file_path).name
        
        in_gitignore = rel_path in gitignore_content or file_name in gitignore_content
        in_cursorignore = rel_path in cursorignore_content or file_name in cursorignore_content
        
        if in_gitignore and in_cursorignore:
            results["both"].append(file_path)
        elif in_gitignore:
            results["gitignore"].append(file_path)
        elif in_cursorignore:
            results["cursorignore"].append(file_path)
        else:
            results["none"].append(file_path)
    
    return results

def check_trash(root, trash_folder="_trash"):
    """Проверяет, какие файлы перемещены в _trash"""
    trash_dir = root / trash_folder
    if not trash_dir.exists():
        return []
    
    trash_files = []
    for item in trash_dir.rglob("*"):
        if item.is_file():
            trash_files.append(item.relative_to(root))
    
    return trash_files

def read_ghost_stats(root):
    """Читает статистику Ghost Protocol"""
    stats_file = root / ".ghost_stats.json"
    if stats_file.exists():
        try:
            return json.loads(stats_file.read_text())
        except:
            return None
    return None

def main():
    # Определяем корень проекта (текущая директория)
    root = Path.cwd()
    
    print_header("GHOST PROTOCOL DETECTION TEST")
    print("\n⚠️  ВАЖНО: Запусти Ghost Protocol в другом терминале перед этим тестом!")
    print("    Команда: python main.py")
    print("\n    Нажми Enter когда Ghost Protocol будет запущен...")
    input()
    
    # Очистка старых тестовых файлов
    print_step("0", "Cleaning up old test files...")
    test_files = [
        "dummy.txt",
        "test_large.txt",
        "test_data.csv",
        "test_junk.log",
        "FULL_PROJECT_CODE.txt",
        "dump_backup.sql",
        "test/src/test_code.py"
    ]
    
    for f in test_files:
        p = root / f
        if p.exists():
            p.unlink()
            print(f"    ✓ Removed old: {f}")
    
    # Очистка trash
    trash_dir = root / "_trash"
    if trash_dir.exists():
        for item in trash_dir.rglob("test*"):
            if item.is_file():
                item.unlink()
    
    time.sleep(1)
    
    # Тест 1: Маленький .txt файл (должен быть UNKNOWN)
    print_step("1", "Creating small .txt file (should be UNKNOWN)...")
    create_test_file(root / "dummy.txt", size_kb=1, content="Test content")
    time.sleep(2)  # Ждём обработки
    
    # Тест 2: Большой .txt файл (> 50KB, должен быть JUNK)
    print_step("2", "Creating large .txt file (> 50KB, should be JUNK)...")
    create_test_file(root / "test_large.txt", size_kb=60)
    time.sleep(2)
    
    # Тест 3: Файл с паттерном мусора (должен быть JUNK)
    print_step("3", "Creating file matching junk pattern (should be JUNK)...")
    create_test_file(root / "FULL_PROJECT_CODE.txt", size_kb=10, content="Project dump")
    time.sleep(2)
    
    # Тест 4: Большой .log файл (должен быть JUNK)
    print_step("4", "Creating large .log file (should be JUNK)...")
    create_test_file(root / "test_junk.log", size_kb=30)
    time.sleep(2)
    
    # Тест 5: Большой .csv файл (должен быть DATA - только .gitignore)
    print_step("5", "Creating large .csv file (should be DATA - .gitignore only)...")
    create_test_file(root / "test_data.csv", size_kb=100, content="col1,col2\n1,2\n")
    time.sleep(2)
    
    # Тест 6: Очень большой файл (> 2MB, должен быть TRASH)
    print_step("6", "Creating huge file (> 2MB, should be TRASH)...")
    create_test_file(root / "dump_backup.sql", size_kb=2500)  # ~2.5MB
    time.sleep(3)  # Больше времени для больших файлов
    
    # Тест 7: Код в папке src/ (должен быть CODE - защищён)
    print_step("7", "Creating code file in src/ (should be CODE - protected)...")
    (root / "test").mkdir(exist_ok=True)
    (root / "test" / "src").mkdir(exist_ok=True)
    create_test_file(root / "test" / "src" / "test_code.py", size_kb=5, content="# Test code\nprint('hello')")
    time.sleep(2)
    
    print_step("8", "Waiting for Ghost to process all files (5 seconds)...")
    time.sleep(5)
    
    # Проверка результатов
    print_header("TEST RESULTS")
    
    # Проверка игнор-файлов
    print_step("CHECK", "Checking .gitignore and .cursorignore...")
    test_paths = [
        Path("dummy.txt"),
        Path("test_large.txt"),
        Path("FULL_PROJECT_CODE.txt"),
        Path("test_junk.log"),
        Path("test_data.csv"),
        Path("dump_backup.sql"),
    ]
    
    ignore_results = check_ignore_files(root, test_paths)
    
    print("\n  Files in BOTH (.gitignore + .cursorignore) [JUNK]:")
    if ignore_results["both"]:
        for f in ignore_results["both"]:
            print(f"    ✓ {f}")
    else:
        print("    ✗ None")
    
    print("\n  Files in .gitignore ONLY [DATA]:")
    if ignore_results["gitignore"]:
        for f in ignore_results["gitignore"]:
            print(f"    ✓ {f}")
    else:
        print("    ✗ None")
    
    print("\n  Files in .cursorignore ONLY:")
    if ignore_results["cursorignore"]:
        for f in ignore_results["cursorignore"]:
            print(f"    ⚠ {f} (unexpected)")
    else:
        print("    - None")
    
    print("\n  Files NOT ignored [UNKNOWN/CODE]:")
    if ignore_results["none"]:
        for f in ignore_results["none"]:
            print(f"    - {f}")
    else:
        print("    - None")
    
    # Проверка _trash
    print_step("CHECK", "Checking _trash folder...")
    trash_files = check_trash(root)
    if trash_files:
        print("\n  Files moved to _trash:")
        for f in trash_files:
            print(f"    ✓ {f}")
    else:
        print("\n    ✗ No files in _trash")
    
    # Статистика Ghost
    print_step("CHECK", "Ghost Protocol Stats:")
    stats = read_ghost_stats(root)
    if stats:
        print(f"\n  Total Tokens: {stats.get('total_tokens', 0):,}")
        print(f"  Tokens Saved: {stats.get('saved_tokens', 0):,}")
        print(f"  Files Tracked: {stats.get('files_count', 0)}")
    else:
        print("\n    ✗ No stats file found")
    
    # Ожидаемые результаты
    print_header("EXPECTED RESULTS")
    print("\n  ✓ dummy.txt → UNKNOWN (не игнорируется)")
    print("  ✓ test_large.txt → JUNK (оба игнора)")
    print("  ✓ FULL_PROJECT_CODE.txt → JUNK (оба игнора)")
    print("  ✓ test_junk.log → JUNK (оба игнора)")
    print("  ✓ test_data.csv → DATA (только .gitignore)")
    print("  ✓ dump_backup.sql → TRASH (перемещён в _trash)")
    print("  ✓ test/src/test_code.py → CODE (не трогаем)")
    
    print_header("NEXT STEPS")
    print("\n  1. Проверь Activity Log в Ghost Protocol Monitor")
    print("  2. Проверь содержимое .gitignore и .cursorignore")
    print("  3. Проверь папку _trash/")
    print("  4. Удали тестовые файлы вручную после проверки")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()

