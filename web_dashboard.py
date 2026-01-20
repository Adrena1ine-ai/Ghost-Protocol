"""
Веб-интерфейс для мониторинга Ghost Protocol
Показывает все проекты, на которых запущен Ghost Protocol
"""
import json
import os
import psutil
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from typing import Dict, List, Any, Optional

app = Flask(__name__)

# Путь к директории с ботами
BOTS_DIR = Path("/opt/bots")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ghost Protocol Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            color: #00d4ff;
            margin-bottom: 10px;
            font-size: 32px;
        }
        
        .subtitle {
            color: #888;
            margin-bottom: 30px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #00d4ff;
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: #888;
            font-size: 14px;
        }
        
        .projects-list {
            display: grid;
            gap: 20px;
        }
        
        .project-card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            transition: border-color 0.3s;
        }
        
        .project-card:hover {
            border-color: #00d4ff;
        }
        
        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .project-name {
            font-size: 20px;
            font-weight: bold;
            color: #00d4ff;
        }
        
        .project-status {
            padding: 5px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status-active {
            background: #00ff88;
            color: #000;
        }
        
        .status-inactive {
            background: #666;
            color: #fff;
        }
        
        .project-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .info-item {
            display: flex;
            flex-direction: column;
        }
        
        .info-label {
            color: #888;
            font-size: 12px;
            margin-bottom: 5px;
        }
        
        .info-value {
            color: #e0e0e0;
            font-size: 16px;
        }
        
        .refresh-btn {
            background: #00d4ff;
            color: #000;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            margin-bottom: 20px;
        }
        
        .refresh-btn:hover {
            background: #00b8d4;
        }
        
        .no-projects {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        
        .path {
            color: #666;
            font-family: monospace;
            font-size: 12px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>👻 Ghost Protocol Dashboard</h1>
        <p class="subtitle">Мониторинг активных проектов</p>
        
        <button class="refresh-btn" onclick="loadData()">🔄 Обновить</button>
        
        <div class="stats-grid" id="stats">
            <!-- Stats will be loaded here -->
        </div>
        
        <div class="projects-list" id="projects">
            <!-- Projects will be loaded here -->
        </div>
    </div>
    
    <script>
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        function formatNumber(num) {
            return num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, " ");
        }
        
        function formatTimeEkaterinburg(timestamp) {
            if (!timestamp) return 'Никогда';
            const date = new Date(timestamp * 1000); // Если timestamp в секундах
            if (isNaN(date.getTime())) {
                // Попробуем как ISO строку
                const date2 = new Date(timestamp);
                if (isNaN(date2.getTime())) return timestamp;
                const ekaterinburgTime = new Date(date2.getTime() + (5 * 60 * 60 * 1000));
                const hours = String(ekaterinburgTime.getUTCHours()).padStart(2, '0');
                const minutes = String(ekaterinburgTime.getUTCMinutes()).padStart(2, '0');
                const day = String(ekaterinburgTime.getUTCDate()).padStart(2, '0');
                const month = String(ekaterinburgTime.getUTCMonth() + 1).padStart(2, '0');
                const year = ekaterinburgTime.getUTCFullYear();
                return `${day}.${month}.${year} ${hours}:${minutes}`;
            }
            // Конвертируем в UTC+5 (Екатеринбург)
            const ekaterinburgTime = new Date(date.getTime() + (5 * 60 * 60 * 1000));
            const hours = String(ekaterinburgTime.getUTCHours()).padStart(2, '0');
            const minutes = String(ekaterinburgTime.getUTCMinutes()).padStart(2, '0');
            const day = String(ekaterinburgTime.getUTCDate()).padStart(2, '0');
            const month = String(ekaterinburgTime.getUTCMonth() + 1).padStart(2, '0');
            const year = ekaterinburgTime.getUTCFullYear();
            return `${day}.${month}.${year} ${hours}:${minutes}`;
        }
        
        function loadData() {
            fetch('/api/projects')
                .then(res => res.json())
                .then(data => {
                    // Update stats
                    const statsHtml = `
                        <div class="stat-card">
                            <div class="stat-value">${data.total_projects}</div>
                            <div class="stat-label">Всего проектов</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.active_projects}</div>
                            <div class="stat-label">Активных</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${formatNumber(data.total_files)}</div>
                            <div class="stat-label">Файлов</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${formatNumber(data.total_tokens)}</div>
                            <div class="stat-label">Токенов</div>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;
                    
                    // Update projects
                    if (data.projects.length === 0) {
                        document.getElementById('projects').innerHTML = 
                            '<div class="no-projects">Нет активных проектов с Ghost Protocol</div>';
                        return;
                    }
                    
                    const projectsHtml = data.projects.map(project => `
                        <div class="project-card">
                            <div class="project-header">
                                <div>
                                    <div class="project-name">${project.name}</div>
                                    <div class="path">${project.path}</div>
                                </div>
                                <span class="project-status ${project.active ? 'status-active' : 'status-inactive'}">
                                    ${project.active ? '● Активен' : '○ Неактивен'}
                                </span>
                            </div>
                            <div class="project-info">
                                <div class="info-item">
                                    <div class="info-label">Файлов</div>
                                    <div class="info-value">${formatNumber(project.files_count || 0)}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Токенов</div>
                                    <div class="info-value">${formatNumber(project.total_tokens || 0)}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Размер</div>
                                    <div class="info-value">${formatBytes(project.total_size || 0)}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Последнее обновление</div>
                                    <div class="info-value">${formatTimeEkaterinburg(project.last_scan)}</div>
                                </div>
                            </div>
                        </div>
                    `).join('');
                    
                    document.getElementById('projects').innerHTML = projectsHtml;
                })
                .catch(err => {
                    console.error('Error loading data:', err);
                });
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 5 seconds
        setInterval(loadData, 5000);
    </script>
</body>
</html>
"""

def find_ghost_projects() -> List[Path]:
    """Найти все проекты с Ghost Protocol"""
    projects = []
    found_paths = set()
    
    # 1. Ищем в /opt/bots
    if BOTS_DIR.exists():
        for item in BOTS_DIR.iterdir():
            if item.is_dir():
                ghost_config = item / "ghost_config.json"
                ghost_stats = item / ".ghost_stats.json"
                
                # Проверяем, есть ли Ghost Protocol
                if ghost_config.exists() or ghost_stats.exists():
                    if item not in found_paths:
                        projects.append(item)
                        found_paths.add(item)
    
    # 2. Ищем активные процессы Ghost Protocol и добавляем их проекты
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        try:
            cmdline = proc.info.get('cmdline', [])
            cwd = proc.info.get('cwd', '')
            
            if cmdline and 'main.py' in ' '.join(cmdline):
                cmdline_str = ' '.join(cmdline) if cmdline else ''
                if 'Ghost Protocol' in cmdline_str or 'ghost' in cmdline_str.lower():
                    # Пытаемся найти корень проекта
                    project_path = Path(cwd) if cwd else None
                    
                    # Или ищем в cmdline
                    if not project_path or not project_path.exists():
                        for arg in cmdline:
                            if arg and Path(arg).exists() and Path(arg).is_dir():
                                potential_project = Path(arg)
                                if (potential_project / "ghost_config.json").exists() or \
                                   (potential_project / ".ghost_stats.json").exists():
                                    project_path = potential_project
                                    break
                    
                    if project_path and project_path.exists() and project_path not in found_paths:
                        projects.append(project_path)
                        found_paths.add(project_path)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return projects

def get_project_stats(project_path: Path) -> Dict[str, Any]:
    """Получить статистику проекта"""
    stats = {
        "name": project_path.name,
        "path": str(project_path),
        "active": False,
        "files_count": 0,
        "total_tokens": 0,
        "saved_tokens": 0,
        "total_size": 0,
        "last_scan": None,
        "pid": None
    }
    
    # Проверяем, запущен ли процесс Ghost Protocol для этого проекта
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        try:
            cmdline = proc.info.get('cmdline', [])
            cwd = proc.info.get('cwd', '')
            
            if cmdline and 'main.py' in ' '.join(cmdline):
                # Проверяем, что это Ghost Protocol и работает в этом проекте
                cmdline_str = ' '.join(cmdline) if cmdline else ''
                if ('Ghost Protocol' in cmdline_str or 
                    str(project_path) in cwd or 
                    str(project_path) in cmdline_str):
                    stats["active"] = True
                    stats["pid"] = proc.info['pid']
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # Читаем кэш статистики
    cache_file = project_path / ".ghost_stats.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                stats["files_count"] = cached.get("files_count", 0)
                stats["total_tokens"] = cached.get("total_tokens", 0)
                stats["saved_tokens"] = cached.get("saved_tokens", 0)
                
                # Вычисляем размер (примерно: токены * 4 байта)
                stats["total_size"] = stats["total_tokens"] * 4
                
                # Время последнего сканирования (может быть timestamp или строка)
                if "last_scan" in cached:
                    last_scan = cached["last_scan"]
                    try:
                        # Если это timestamp
                        if isinstance(last_scan, (int, float)):
                            # Конвертируем в UTC+5 (Екатеринбург)
                            from datetime import timezone, timedelta
                            ekaterinburg_tz = timezone(timedelta(hours=5))
                            scan_time = datetime.fromtimestamp(last_scan, tz=timezone.utc)
                            ekaterinburg_time = scan_time.astimezone(ekaterinburg_tz)
                            stats["last_scan"] = ekaterinburg_time.strftime("%d.%m.%Y %H:%M")
                        else:
                            stats["last_scan"] = str(last_scan)
                    except:
                        stats["last_scan"] = str(last_scan)
        except Exception as e:
            pass
    
    return stats

@app.route('/')
def index():
    """Главная страница"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/projects')
def api_projects():
    """API для получения списка проектов"""
    projects = find_ghost_projects()
    
    project_stats = []
    total_files = 0
    total_tokens = 0
    active_count = 0
    
    for project_path in projects:
        stats = get_project_stats(project_path)
        project_stats.append(stats)
        
        total_files += stats["files_count"]
        total_tokens += stats["total_tokens"]
        if stats["active"]:
            active_count += 1
    
    return jsonify({
        "total_projects": len(projects),
        "active_projects": active_count,
        "total_files": total_files,
        "total_tokens": total_tokens,
        "projects": project_stats
    })

if __name__ == '__main__':
    print("🌐 Ghost Protocol Dashboard доступен по адресу: http://localhost:5001")
    print("📊 Откройте в браузере для просмотра проектов")
    app.run(host='0.0.0.0', port=5001, debug=False)

