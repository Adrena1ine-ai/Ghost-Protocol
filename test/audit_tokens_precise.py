#!/usr/bin/env python3
"""
PRECISE TOKEN AUDIT
Сравнение подсчёта токенов по размеру (байты // 4) vs реальные токены
"""

import os
import fnmatch
from pathlib import Path
from typing import List, Tuple, Dict

# Пробуем импортировать tiktoken для точного подсчёта
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
    # Для Python кода используем cl100k_base (GPT-4 токенизатор)
    enc = tiktoken.get_encoding("cl100k_base")
except ImportError:
    TIKTOKEN_AVAILABLE = False
    enc = None

def count_real_tokens(file_path: Path, content: str) -> int:
    """Подсчитывает реальные токены через tiktoken"""
    if not TIKTOKEN_AVAILABLE:
        return 0
    
    try:
        # Для Python файлов используем cl100k_base
        if file_path.suffix == ".py":
            return len(enc.encode(content))
        # Для остальных - тоже пробуем (работает для большинства текстовых форматов)
        else:
            return len(enc.encode(content))
    except Exception:
        return 0

def scan_project_precise(root: Path) -> Dict:
    """
    Сканирует проект и считает токены двумя способами:
    1. По размеру (байты // 4) - приблизительно
    2. Реальные токены через tiktoken (если доступен) - точно
    """
    
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
    
    total_by_size = 0  # Подсчёт по размеру (байты // 4)
    total_real = 0      # Реальные токены через tiktoken
    file_stats: List[Tuple[str, int, int]] = []  # (путь, по размеру, реальные)
    
    print(f"Scanning: {root}")
    print(f"Tiktoken available: {TIKTOKEN_AVAILABLE}")
    if not TIKTOKEN_AVAILABLE:
        print("  Install tiktoken for precise counting: pip install tiktoken")
    print()
    
    files_processed = 0
    files_with_real_tokens = 0
    
    for root_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        
        for file in files:
            file_path = Path(root_dir) / file
            
            if file.startswith(".") or file.startswith("~"):
                continue
            
            try:
                if file_path.suffix.lower() not in SAFE_TEXT_EXTENSIONS:
                    continue
                
                # Читаем файл
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                
                # Подсчёт по размеру
                size_bytes = len(content.encode('utf-8'))
                tokens_by_size = size_bytes // 4
                
                # Реальные токены (только если tiktoken доступен)
                real_tokens = 0
                if TIKTOKEN_AVAILABLE:
                    real_tokens = count_real_tokens(file_path, content)
                    if real_tokens > 0:
                        files_with_real_tokens += 1
                
                rel_path = str(file_path.relative_to(root)).replace("\\", "/")
                
                total_by_size += tokens_by_size
                total_real += real_tokens
                file_stats.append((rel_path, tokens_by_size, real_tokens))
                files_processed += 1
                
            except (OSError, ValueError):
                continue
    
    # Сортируем по размеру (по размеру в байтах)
    file_stats.sort(key=lambda x: x[1], reverse=True)
    
    return {
        'total_by_size': total_by_size,
        'total_real': total_real,
        'files_processed': files_processed,
        'files_with_real_tokens': files_with_real_tokens,
        'top_10': file_stats[:10]
    }

def main():
    root = Path.cwd()
    
    print("=" * 70)
    print("PRECISE TOKEN AUDIT")
    print("=" * 70)
    print()
    
    results = scan_project_precise(root)
    
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    print(f"Files processed: {results['files_processed']}")
    if TIKTOKEN_AVAILABLE:
        print(f"Files with real token count: {results['files_with_real_tokens']}")
    print()
    print("Token Count Comparison:")
    print("-" * 70)
    print(f"{'Method':<30} {'Tokens':>15} {'Percentage':>15}")
    print("-" * 70)
    
    size_tokens = results['total_by_size']
    real_tokens = results['total_real']
    
    print(f"{'By Size (bytes // 4)':<30} {size_tokens:>15,}")
    
    if TIKTOKEN_AVAILABLE and real_tokens > 0:
        print(f"{'Real Tokens (tiktoken)':<30} {real_tokens:>15,}")
        diff = abs(size_tokens - real_tokens)
        diff_pct = (diff / real_tokens * 100) if real_tokens > 0 else 0
        print(f"{'Difference':<30} {diff:>15,} ({diff_pct:.1f}%)")
        print()
        print(f"Accuracy: {100 - diff_pct:.1f}%")
    else:
        print()
        print("Install tiktoken for precise comparison:")
        print("  pip install tiktoken")
    
    print()
    print("Top 10 Files (by size method):")
    print("-" * 70)
    print(f"{'File':<50} {'Size Method':>15} {'Real Tokens':>15}")
    print("-" * 70)
    
    for file_path, size_tok, real_tok in results['top_10']:
        display_path = file_path if len(file_path) <= 48 else "..." + file_path[-45:]
        real_str = f"{real_tok:,}" if real_tok > 0 else "N/A"
        print(f"{display_path:<50} {size_tok:>15,} {real_str:>15}")
    
    print("=" * 70)
    
    if TIKTOKEN_AVAILABLE and real_tokens > 0:
        print()
        print("CONCLUSION:")
        if abs(size_tokens - real_tokens) / real_tokens < 0.1:  # < 10% разница
            print("  [OK] Size-based method is reasonably accurate (<10% error)")
        elif abs(size_tokens - real_tokens) / real_tokens < 0.25:  # < 25% разница
            print("  [WARN] Size-based method has moderate error (10-25%)")
        else:
            print("  [ERROR] Size-based method has significant error (>25%)")
        print("  Formula: tokens = bytes // 4 is an approximation")
        print("  Real tokenizers use subword encoding (BPE), which varies")

if __name__ == "__main__":
    main()


