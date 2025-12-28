"""
Простой тест Ghost Protocol с git commit

ВАЖНО: Ghost Protocol работает как файловый watcher, 
а не как git hook. Он обнаруживает файлы при их СОЗДАНИИ/ИЗМЕНЕНИИ,
а не при git commit.

Этот тест проверяет:
1. Создание файла → обнаружение watcher'ом
2. Классификацию → добавление в игнор или trash
3. Git операции (для полноты теста)
"""

import os
import subprocess
from pathlib import Path
import time

def run_cmd(cmd, cwd=None):
    """Выполняет команду и выводит результат"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.stdout:
            print(f"  Output: {result.stdout.strip()}")
        if result.stderr and result.returncode != 0:
            print(f"  Error: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"  Exception: {e}")
        return False

def main():
    root = Path.cwd()
    
    print("\n" + "="*70)
    print("  GHOST PROTOCOL SIMPLE TEST (with git)")
    print("="*70)
    
    print("\n⚠️  Убедись, что Ghost Protocol запущен в другом терминале!")
    print("    Команда: python main.py")
    input("\n    Нажми Enter когда готов...")
    
    test_file = root / "dummy.txt"
    
    # Очистка
    if test_file.exists():
        test_file.unlink()
        print("\n[1] Удалил старый dummy.txt")
    
    # Создание файла
    print("\n[2] Создаю файл dummy.txt...")
    test_file.write_text("This is a test file for Ghost Protocol", encoding='utf-8')
    print(f"    ✓ Файл создан: {test_file}")
    
    # Ждём обработки Ghost (debounce = 0.5 сек)
    print("\n[3] Жду обработки Ghost Protocol (2 секунды)...")
    time.sleep(2)
    
    # Проверка игнор-файлов
    print("\n[4] Проверяю игнор-файлы...")
    gitignore = root / ".gitignore"
    cursorignore = root / ".cursorignore"
    
    if gitignore.exists():
        gitignore_content = gitignore.read_text(encoding='utf-8')
        if "dummy.txt" in gitignore_content:
            print("    ✓ dummy.txt найден в .gitignore")
        else:
            print("    ✗ dummy.txt НЕ найден в .gitignore")
    else:
        print("    ✗ .gitignore не существует")
    
    if cursorignore.exists():
        cursorignore_content = cursorignore.read_text(encoding='utf-8')
        if "dummy.txt" in cursorignore_content:
            print("    ✓ dummy.txt найден в .cursorignore")
        else:
            print("    ✗ dummy.txt НЕ найден в .cursorignore")
    else:
        print("    ✗ .cursorignore не существует")
    
    # Проверка _trash
    print("\n[5] Проверяю папку _trash...")
    trash_dir = root / "_trash"
    if trash_dir.exists():
        trash_dummy = trash_dir / "dummy.txt"
        if trash_dummy.exists():
            print(f"    ✓ dummy.txt перемещён в _trash")
        else:
            print("    ✗ dummy.txt НЕ в _trash")
    else:
        print("    ✗ Папка _trash не существует")
    
    # Git операции (для полноты теста)
    print("\n[6] Тестирую git операции...")
    
    # Проверка git статуса
    if run_cmd("git status --short", cwd=root):
        print("    ✓ Git status работает")
    
    # Git add (это НЕ триггерит Ghost, файл уже создан)
    print("\n[7] Добавляю файл в git (git add)...")
    run_cmd(f"git add {test_file}", cwd=root)
    print("    ⚠️  Примечание: git add не триггерит Ghost (файл уже обработан)")
    
    # Проверка staged файлов
    result = subprocess.run("git diff --cached --name-only", shell=True, cwd=root, 
                          capture_output=True, text=True)
    if "dummy.txt" in result.stdout:
        print("    ✓ dummy.txt staged для commit")
    else:
        print("    ✗ dummy.txt НЕ staged (возможно, в .gitignore)")
    
    print("\n[8] Создаю commit...")
    run_cmd('git commit -m "Test: Ghost Protocol detection"', cwd=root)
    print("    ⚠️  Примечание: git commit также не триггерит Ghost")
    
    print("\n" + "="*70)
    print("  РЕЗУЛЬТАТЫ ТЕСТА")
    print("="*70)
    
    print("\n✅ ЧТО ДОЛЖНО БЫЛО ПРОИЗОЙТИ:")
    print("   1. Watcher обнаружил создание dummy.txt")
    print("   2. FileClassifier классифицировал файл")
    print("   3. Файл добавлен в игнор или перемещён в trash")
    print("   4. В Activity Log появилось сообщение")
    
    print("\n📋 ПРОВЕРЬ В GHOST PROTOCOL MONITOR:")
    print("   - Activity Log (правая колонка)")
    print("   - Содержимое .gitignore и .cursorignore")
    print("   - Папку _trash/")
    
    print("\n⚠️  ВАЖНО:")
    print("   - Ghost работает как файловый WATCHER, не как git hook")
    print("   - Он обнаруживает файлы при СОЗДАНИИ/ИЗМЕНЕНИИ в файловой системе")
    print("   - git commit сам по себе НЕ триггерит Ghost")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()

