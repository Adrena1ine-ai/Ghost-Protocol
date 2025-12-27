# Инструкция по публикации на PyPI

## Шаг 1: Подготовка

Убедитесь, что все файлы готовы:
- ✅ `pyproject.toml` настроен
- ✅ Версия обновлена (1.0.0)
- ✅ README.md готов
- ✅ LICENSE файл присутствует

## Шаг 2: Установка инструментов для публикации

```bash
pip install build twine
```

## Шаг 3: Сборка пакета

```bash
python -m build
```

Это создаст папку `dist/` с файлами:
- `ghost-protocol-1.0.0.tar.gz` (исходный код)
- `ghost_protocol-1.0.0-py3-none-any.whl` (wheel файл)

## Шаг 4: Проверка пакета (опционально)

```bash
# Проверка на ошибки
python -m twine check dist/*
```

## Шаг 5: Регистрация на PyPI

1. Создайте аккаунт на https://pypi.org/account/register/
2. Подтвердите email
3. Создайте API токен на https://pypi.org/manage/account/token/
   - Scope: "Entire account" или "Project: ghost-protocol"
   - Сохраните токен в безопасном месте

## Шаг 6: Публикация на PyPI

### Первая публикация (TestPyPI для тестирования):

```bash
# Загрузить на TestPyPI (для тестирования)
python -m twine upload --repository testpypi dist/*

# Установить с TestPyPI для проверки
pip install --index-url https://test.pypi.org/simple/ ghost-protocol
```

### Публикация на основной PyPI:

```bash
# Загрузить на PyPI
python -m twine upload dist/*
```

Введите ваши учетные данные PyPI (username: `__token__`, password: ваш API токен)

## Шаг 7: Установка и проверка

После публикации подождите несколько минут, затем:

```bash
# Установка пакета
pip install ghost-protocol

# Проверка работы команды
ghost --help
ghost --install
```

## Важные замечания

1. **Имя пакета**: `ghost-protocol` (с дефисом)
   - Команда установки: `pip install ghost-protocol`
   - Команда в терминале: `ghost` (без дефиса)

2. **Обновление версии**: При каждом обновлении меняйте версию в `pyproject.toml` и пересобирайте пакет

3. **Проверка доступности имени**: Убедитесь, что имя `ghost-protocol` свободно на PyPI

## Проверка доступности имени пакета

Проверьте, свободно ли имя:
- Откройте https://pypi.org/project/ghost-protocol/
- Если страница не существует или показывает "404", имя свободно

## Альтернатива: Изменить имя на "ghost"

Если хотите, чтобы установка была `pip install ghost`, нужно:
1. Изменить `name = "ghost-protocol"` на `name = "ghost"` в `pyproject.toml`
2. Проверить доступность имени "ghost" на PyPI (скорее всего занято)

**Рекомендация**: Оставьте `ghost-protocol`, так как короткие имена обычно заняты.

