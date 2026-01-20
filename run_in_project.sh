#!/bin/bash
# Скрипт для запуска Ghost Protocol в другом проекте
# Использование: ./run_in_project.sh /path/to/other/project

if [ -z "$1" ]; then
    echo "Использование: $0 /path/to/project"
    echo "Пример: $0 /opt/bots/CINTYPLAY"
    exit 1
fi

PROJECT_PATH="$1"
GHOST_PROTOCOL_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$PROJECT_PATH" ]; then
    echo "Ошибка: Директория '$PROJECT_PATH' не существует"
    exit 1
fi

if [ ! -d "$PROJECT_PATH/.git" ]; then
    echo "Предупреждение: '$PROJECT_PATH' не является git-репозиторием"
    echo "Ghost Protocol работает лучше в git-репозиториях"
    read -p "Продолжить? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Запуск Ghost Protocol для проекта: $PROJECT_PATH"
echo "Ghost Protocol находится в: $GHOST_PROTOCOL_DIR"
echo ""

cd "$PROJECT_PATH"
python3 "$GHOST_PROTOCOL_DIR/main.py"

