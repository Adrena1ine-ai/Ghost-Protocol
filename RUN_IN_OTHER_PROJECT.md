# 🚀 Запуск Ghost Protocol в другом проекте

## Вариант 1: Использование скрипта (Рекомендуется)

Создан скрипт `run_in_project.sh` для удобного запуска:

```bash
cd "/opt/bots/Ghost Protocol"
./run_in_project.sh /path/to/your/other/project
```

**Пример:**
```bash
./run_in_project.sh /opt/bots/CINTYPLAY
./run_in_project.sh /opt/bots/fox-pro-ai-v4
```

## Вариант 2: Ручной запуск

### Шаг 1: Перейти в директорию другого проекта
```bash
cd /path/to/your/other/project
```

### Шаг 2: Запустить Ghost Protocol
```bash
python3 "/opt/bots/Ghost Protocol/main.py"
```

Или если `ghost` установлен глобально:
```bash
ghost
```

## Вариант 3: Запуск в фоновом режиме (для сервера)

### Использование nohup:
```bash
cd /path/to/your/other/project
nohup python3 "/opt/bots/Ghost Protocol/main.py" > ghost.log 2>&1 &
```

### Использование screen:
```bash
screen -S ghost-other-project
cd /path/to/your/other/project
python3 "/opt/bots/Ghost Protocol/main.py"
# Нажмите Ctrl+A затем D для отсоединения
```

### Использование tmux:
```bash
tmux new -s ghost-other-project
cd /path/to/your/other/project
python3 "/opt/bots/Ghost Protocol/main.py"
# Нажмите Ctrl+B затем D для отсоединения
```

## Вариант 4: Создание systemd сервиса (для постоянной работы)

Создайте файл `/etc/systemd/system/ghost-protocol-other.service`:

```ini
[Unit]
Description=Ghost Protocol для другого проекта
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/your/other/project
ExecStart=/usr/bin/python3 /opt/bots/Ghost Protocol/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ghost-protocol-other
sudo systemctl start ghost-protocol-other
sudo systemctl status ghost-protocol-other
```

## ⚠️ Важные замечания

1. **Git-репозиторий**: Ghost Protocol работает лучше в git-репозиториях. Если проекта нет в git, запустите `git init` сначала.

2. **Независимые конфигурации**: Каждый проект имеет свой `ghost_config.json`. Настройки не пересекаются.

3. **Параллельный запуск**: Можно запускать Ghost Protocol для нескольких проектов одновременно. Каждый процесс работает независимо.

4. **Порты**: Ghost Protocol не использует сетевые порты, поэтому конфликтов портов не будет.

5. **Ресурсы**: Каждый экземпляр Ghost Protocol использует ресурсы системы. На сервере с ограниченными ресурсами учитывайте это.

## 📋 Примеры для проектов на этом сервере

На вашем сервере есть следующие проекты:
- `/opt/bots/CINTYPLAY`
- `/opt/bots/fox-pro-ai-v4`
- `/opt/bots/ai_toolkit`
- `/opt/bots/vpn-proxy`

**Запуск для CINTYPLAY:**
```bash
cd "/opt/bots/Ghost Protocol"
./run_in_project.sh /opt/bots/CINTYPLAY
```

**Запуск для fox-pro-ai-v4:**
```bash
cd "/opt/bots/Ghost Protocol"
./run_in_project.sh /opt/bots/fox-pro-ai-v4
```

## 🔍 Проверка запущенных процессов

Чтобы увидеть все запущенные экземпляры Ghost Protocol:
```bash
ps aux | grep "[m]ain.py"
```

Или более детально:
```bash
ps aux | grep -E "Ghost Protocol|main.py" | grep -v grep
```

