import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich.live import Live
from .config import Config, VERSION
from .scanner import ProjectScanner
from .ai_reviewer import AIReviewer
from .analyzer import CodeAnalyzer
from .watcher import VibeWatcher, Observer, process_queue
from typing import List
import queue
from .core import logger

# Настройка таймзоны Ekaterinburg (+5)
EKB_TZ = timezone(timedelta(hours=5))

COST_PER_M_TOKENS = 3.0
SCAN_INTERVAL_SECONDS = 30

class Monitor:
    def __init__(self, root: Path, scanner, task_queue, shutdown_event, ignore_mgr):
        # Убеждаемся что scanner имеет ignore_mgr для фильтрации Top 10
        if hasattr(scanner, 'ignore_mgr') and scanner.ignore_mgr is None:
            scanner.ignore_mgr = ignore_mgr
        self.root = root
        self.scanner = scanner # Передаем готовый сканер
        self.task_queue = task_queue
        self.shutdown_event = shutdown_event
        self.ignore_mgr = ignore_mgr
        self.cfg = Config.get()
        self.console = Console()
        
        # Инициализация модулей
        self.ai_reviewer = AIReviewer(root)
        self.analyzer = CodeAnalyzer(root)
        self.last_prompt_status = "No prompt"
        self.observer = None
        self.activity_logs: List[str] = []  # Логи активности для отображения
        self.max_log_lines = 10
        self._last_top_files: List = []  # Кэш последних top_files (чтобы не мигало)

    def _get_time_str(self):
        return datetime.now(EKB_TZ).strftime("%H:%M:%S")
    
    def add_log(self, message: str):
        """Добавляет сообщение в лог активности"""
        log_entry = f"[{self._get_time_str()}] {message}"
        self.activity_logs.append(log_entry)
        if len(self.activity_logs) > self.max_log_lines * 2:  # Храним больше для истории
            self.activity_logs = self.activity_logs[-self.max_log_lines:]

    def _generate_layout(self) -> Layout:
        stats = self.scanner.get_stats()
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )
        layout["body"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="top10", ratio=1),
            Layout(name="logs", ratio=1)
        )

        layout["header"].update(
            Panel(f"[bold]Ghost Protocol v{VERSION}[/bold] | Status: [bold green]GUARDIAN ACTIVE[/bold green]", style="black on #1e1e1e")
        )

        # Col 1: Stats
        table_stats = Table(box=None, expand=True, show_header=False)
        table_stats.add_column("Metric", style="bright_white", width=15)
        table_stats.add_column("Value", style="bold green")
        
        tokens = stats.get('total_tokens', 0)
        saved_tokens = stats.get('saved_tokens', 0)
        files = stats.get('files_count', 0)
        table_stats.add_row("Total Tokens", f"{tokens:,}")
        table_stats.add_row("Tokens Saved", f"{saved_tokens:,}")
        table_stats.add_row("Files Tracked", str(files))
        
        layout["stats"].update(Panel(table_stats, title="[bright_white]Project Stats[/bright_white]", style="#1e1e1e on #000000"))

        table_top = Table(box=None, expand=True, show_header=True)
        table_top.add_column("File", style="bright_white", header_style="bright_white")
        table_top.add_column("Tokens", style="bright_white", header_style="bright_white", justify="right")
        
        # Отрисовка Top 10 из сканера (с кэшированием)
        top_files = stats.get('top_files', [])
        
        # Если новые данные есть - обновляем кэш
        if top_files:
            self._last_top_files = top_files
        
        # Используем кэш если текущие данные пустые
        display_files = top_files if top_files else self._last_top_files
        
        if display_files:
            for item in display_files:
                # Может быть список [path, tokens] или кортеж (path, tokens)
                if isinstance(item, list) and len(item) == 2:
                    p, tokens = item[0], item[1]
                elif isinstance(item, tuple) and len(item) == 2:
                    p, tokens = item[0], item[1]
                else:
                    continue
                    
                # Форматируем красивый относительный путь (если длинный, обрезаем)
                rel_p = str(p)
                if len(rel_p) > 30:
                    rel_p = "..." + rel_p[-27:]
                # Форматируем токены (K/M)
                tokens = int(tokens) if isinstance(tokens, (int, float)) else 0
                if tokens >= 1_000_000:
                    tokens_str = f"{tokens / 1_000_000:.1f}M"
                elif tokens >= 1_000:
                    tokens_str = f"{tokens / 1_000:.1f}K"
                else:
                    tokens_str = f"{tokens:,}"
                table_top.add_row(rel_p, tokens_str)
        else:
            table_top.add_row("Scanning...", "-")
        
        layout["top10"].update(Panel(table_top, title="[bright_white]Top Heavy Files[/bright_white]", style="#1e1e1e on #000000"))

        # Col 3: Logs (комбинируем activity_logs + GhostLogHandler)
        log_lines = []
        
        # Получаем логи из GhostLogHandler (если доступен)
        try:
            from .utils import GhostLogHandler
            import logging
            ghost_logs = []
            for handler in logging.getLogger("ghost").handlers:
                if isinstance(handler, GhostLogHandler):
                    ghost_logs = handler.get_logs()
                    break
            if ghost_logs:
                log_lines.extend(ghost_logs[-self.max_log_lines:])
        except Exception:
            pass
        
        # Добавляем activity_logs (если есть)
        if self.activity_logs:
            log_lines.extend(self.activity_logs[-self.max_log_lines:])
        
        # Убираем дубликаты и ограничиваем количество
        seen = set()
        unique_logs = []
        for log in log_lines:
            if log not in seen:
                seen.add(log)
                unique_logs.append(log)
                if len(unique_logs) >= self.max_log_lines:
                    break
        
        if not unique_logs:
            unique_logs = [
                f"[{self._get_time_str()}] System ready.",
                f"[{self._get_time_str()}] Waiting for commands..."
            ]
        
        # Добавляем стили для контрастности (белый/светло-серый текст)
        log_lines_styled = [f"[white]{line}[/white]" for line in unique_logs]
        log_text = "\n".join(log_lines_styled)
        if not log_text.strip():
            log_text = f"[white][{self._get_time_str()}] System ready.[/white]"
        log_text += f"\n[dim white]AI Status: {self.ai_reviewer.get_status()}[/dim white]"
        layout["logs"].update(Panel(log_text, title="[bright_white]Activity Log (+5)[/bright_white]", style="white on #000000"))

        layout["footer"].update(
            Panel(f"CONTROLS: [1] AI Review  [2] Copy Prompt  [3] Full Check", style="black on #000000")
        )
        
        return layout

    def _handle_input(self):
        if sys.platform != "win32":
            return 
        
        import msvcrt
        
        if msvcrt.kbhit():
            key = msvcrt.getch()
            try:
                char = key.decode('utf-8')
            except UnicodeDecodeError:
                return
            
            if char == '1':
                self.console.print("\n[bold yellow]Running AI Review...[/bold yellow]")
                self.ai_reviewer.run_review()
            elif char == '2':
                success, msg = self.ai_reviewer.copy_prompt_to_clipboard()
                self.console.print(f"\n[{'green' if success else 'red'}]{msg}[/]")
            elif char == '3':
                self.console.print("\n[bold yellow]Running Full Project Check...[/bold yellow]")
                report = self.analyzer.full_check()
                self.console.print(report)

    def start(self):
        # Запуск наблюдателя
        self.observer = Observer()
        event_handler = VibeWatcher(self.root, self.task_queue, self.ignore_mgr)
        self.observer.schedule(event_handler, str(self.root), recursive=True)
        self.observer.start()

        if not self.observer.is_alive():
            logger.error("[Ghost] Observer failed to start.")
            self.console.print("[red][ERROR] Ghost failed to start.[/red]")
            return

        logger.info("[Ghost] Watching for file changes...")
        self.console.print("[green][OK] Ghost is now watching your project[/green]")
        self.console.print("[dim]Press Ctrl+C to stop[/dim]")
        
        # Добавляем начальные логи
        stats = self.scanner.get_stats()
        top_files_count = len(stats.get('top_files', []))
        self.add_log("System ready - monitoring file changes")
        if top_files_count > 0:
            self.add_log(f"Top {top_files_count} heavy files tracked")

        try:
            with Live(self._generate_layout(), console=self.console, refresh_per_second=4) as live:
                last_scan = time.time()
                last_layout_update = time.time()
                last_stats_hash = None
                
                self.console.print("\n[bold cyan]CONTROLS:[/bold cyan] [1] AI Review  [2] Copy Prompt  [3] Full Check")
                
                try:
                    while self.observer.is_alive():
                        now = time.time()
                        
                        # Обновление UI только при необходимости:
                        # 1. После сканирования
                        # 2. При изменении статистики
                        # 3. При добавлении новых логов (но не чаще чем раз в 0.5 сек)
                        stats = self.scanner.get_stats()
                        current_stats_hash = hash((stats.get('total_tokens', 0), stats.get('files_count', 0), len(stats.get('top_files', []))))
                        
                        should_update = (
                            current_stats_hash != last_stats_hash or  # Статистика изменилась
                            now - last_layout_update > 0.5 or  # Минимум 0.5 сек между обновлениями
                            len(self.activity_logs) > 0  # Есть новые логи
                        )
                        
                        if should_update:
                            live.update(self._generate_layout())
                            last_layout_update = now
                            last_stats_hash = current_stats_hash
                        
                        # Редкие обновления
                        # Скан проекта каждые 30 сек
                        if now - last_scan > SCAN_INTERVAL_SECONDS:
                            self.add_log("Scanning project...")
                            # Обновляем UI сразу после начала сканирования
                            live.update(self._generate_layout())
                            last_layout_update = now
                            
                            self.scanner.scan_full_project()
                            stats = self.scanner.get_stats()
                            files_count = stats.get('files_count', 0)
                            tokens_count = stats.get('total_tokens', 0)
                            top_count = len(stats.get('top_files', []))
                            self.add_log(f"Scan complete: {files_count} files, {tokens_count:,} tokens, {top_count} top files")
                            
                            # Обновляем UI после сканирования
                            live.update(self._generate_layout())
                            last_layout_update = now
                            last_stats_hash = hash((tokens_count, files_count, top_count))
                            last_scan = now
                        
                        # События теперь приходят через callback (event_callback в process_queue)
                        
                        self._handle_input()
                        time.sleep(0.25)  # Увеличили интервал для снижения нагрузки
                except KeyboardInterrupt:
                    logger.info("[Ghost] Shutting down...")
                    self.shutdown_event.set()
                    self.observer.stop()
                self.observer.join()
            self.console.print("\n[yellow]Ghost stopped.[/yellow]")
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            # Экранируем Rich markup в сообщении об ошибке
            error_msg = str(e).replace("[", "[[").replace("]", "]]")
            self.console.print(f"\n[red]Error: {error_msg}[/red]")
            if self.observer:
                self.observer.stop()
                self.observer.join()
