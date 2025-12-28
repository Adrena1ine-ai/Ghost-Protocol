#!/usr/bin/env python3
"""
AUDIT PROJECT TOKENS
Точная проверка токенов проекта с учётом .cursorignore
"""

import os
import fnmatch
from pathlib import Path
from typing import List, Tuple, Set

def read_cursorignore(root: Path) -> Set[str]:
    """Читает .cursorignore и возвращает набор паттернов"""
    cursorignore_path = root / ".cursorignore"
    patterns = set()
    
    if not cursorignore_path.exists():
        return patterns
    
    try:
        with open(cursorignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Пропускаем комментарии и пустые строки
                if not line or line.startswith('#'):
                    continue
                # Убираем ghost_tag если есть
                if line.endswith('# ghost: auto'):
                    line = line.replace('# ghost: auto', '').strip()
                patterns.add(line)
    except Exception as e:
        print(f"Warning: Could not read .cursorignore: {e}")
    
    return patterns

def matches_pattern(path_str: str, patterns: Set[str]) -> bool:
    """Проверяет, соответствует ли путь какому-либо паттерну из .cursorignore"""
    normalized = path_str.replace("\\", "/").lstrip("/")
    
    for pattern in patterns:
        pattern_clean = pattern.strip()
        
        # Точное совпадение
        if normalized == pattern_clean or normalized.endswith("/" + pattern_clean):
            return True
        
        # Проверка паттернов с *
        if "*" in pattern_clean:
            if fnmatch.fnmatch(normalized, pattern_clean):
                return True
            if fnmatch.fnmatch(Path(normalized).name, pattern_clean):
                return True
        
        # Проверка директорий (если паттерн заканчивается на /)
        if pattern_clean.endswith("/"):
            dir_pattern = pattern_clean.rstrip("/")
            if normalized.startswith(dir_pattern + "/") or normalized == dir_pattern:
                return True
    
    return False

def scan_project(root: Path) -> Tuple[int, List[Tuple[str, int]]]:
    """
    Сканирует проект и возвращает:
    - Общее количество токенов
    - Список (путь, токены) для топ-10 файлов
    """
    cursorignore_patterns = read_cursorignore(root)
    
    total_tokens = 0
    file_tokens: List[Tuple[str, int]] = []
    
    # Расширения, которые считаем текстовыми
    SAFE_TEXT_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss",
        ".java", ".c", ".cpp", ".rs", ".go", ".php", ".rb",
        ".md", ".txt", ".yml", ".yaml", ".json", ".sql"
    }
    
    skip_dirs = {
        ".git", ".venv", "venv", "node_modules", "__pycache__",
        ".idea", ".vscode", ".cursor", "_trash", ".ghost"
    }
    
    print(f"Scanning: {root}")
    print(f"Ignore patterns found: {len(cursorignore_patterns)}")
    if cursorignore_patterns:
        print(f"Sample patterns: {list(cursorignore_patterns)[:5]}")
    print()
    
    for root_dir, dirs, files in os.walk(root):
        # Фильтруем директории
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        
        for file in files:
            file_path = Path(root_dir) / file
            
            # Пропускаем служебные файлы
            if file.startswith(".") or file.startswith("~"):
                continue
            
            try:
                # Получаем относительный путь
                rel_path = str(file_path.relative_to(root)).replace("\\", "/")
                
                # Проверяем, игнорируется ли файл
                if matches_pattern(rel_path, cursorignore_patterns):
                    continue
                
                # Проверяем расширение (только текстовые файлы)
                if file_path.suffix.lower() not in SAFE_TEXT_EXTENSIONS:
                    continue
                
                # Пробуем прочитать как текст (проверка на бинарность)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read(1)  # Читаем первый байт
                except (UnicodeDecodeError, OSError):
                    continue  # Бинарный файл или ошибка доступа
                
                # Получаем размер
                size_bytes = file_path.stat().st_size
                tokens = size_bytes // 4  # 1 токен ≈ 4 байта
                
                total_tokens += tokens
                file_tokens.append((rel_path, tokens))
                
            except (OSError, ValueError) as e:
                # Пропускаем файлы, к которым нет доступа
                continue
    
    # Сортируем по токенам и берём топ-10
    file_tokens.sort(key=lambda x: x[1], reverse=True)
    top_10 = file_tokens[:10]
    
    return total_tokens, top_10

def main():
    root = Path.cwd()
    
    print("=" * 70)
    print("AUDIT PROJECT TOKENS")
    print("=" * 70)
    print()
    
    total_tokens, top_10 = scan_project(root)
    
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    print(f"Total Tokens: {total_tokens:,}")
    print(f"Total Tokens (K): {total_tokens / 1000:.1f}K")
    print(f"Total Tokens (M): {total_tokens / 1_000_000:.2f}M")
    print()
    print("Top 10 Files by Tokens:")
    print("-" * 70)
    print(f"{'File':<50} {'Tokens':>15}")
    print("-" * 70)
    
    for i, (file_path, tokens) in enumerate(top_10, 1):
        # Обрезаем длинные пути
        display_path = file_path if len(file_path) <= 48 else "..." + file_path[-45:]
        tokens_str = f"{tokens:,}"
        print(f"{display_path:<50} {tokens_str:>15}")
    
    print("=" * 70)

if __name__ == "__main__":
    main()


