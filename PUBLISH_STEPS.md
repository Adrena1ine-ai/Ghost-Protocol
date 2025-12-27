# Пошаговая инструкция по публикации на PyPI

## Название пакета: `ghost-protocol`
## Версия: `1.0.0`

## Текущая конфигурация pyproject.toml:

```toml
[project]
name = "ghost-protocol"
version = "1.0.0"
description = "The automated guardian of your sanity. Auto-ignores junk & protects repos."
readme = "README.md"
requires-python = ">=3.8"
license = "MIT"
license-files = ["LICEN[CS]E*"]
authors = [
    {name = "Lazy Vibe Coder", email = "ghost@vibe.com"},
]
```

## ✅ Статус готовности: ВСЁ ГОТОВО К ПУБЛИКАЦИИ

---

## Шаг 1: Создание API токена на PyPI

### ⚠️ ВАЖНО: Для первой публикации используйте "Entire account"

Поскольку проект еще не существует на PyPI, вы не сможете выбрать "Project: ghost-protocol" в scope. Используйте "Entire account" для первой публикации.

1. Войдите на https://pypi.org/account/login/
2. Перейдите в **Account settings** → **API tokens**
3. Нажмите **"Add API token"**
4. Заполните форму:
   - **Token name**: `ghost-protocol-upload` (или любое имя)
   - **Scope**: Выберите **"Entire account"** (для первой публикации)
   - **Expiration**: Выберите срок действия (или "No expiration")
5. Нажмите **"Add token"**
6. **ВАЖНО**: Скопируйте токен сразу! Он начинается с `pypi-` и показывается только один раз
7. Сохраните токен в безопасном месте

### После первой публикации:

После успешной публикации проекта на PyPI, вы сможете создать новый токен с ограничением **"Project: ghost-protocol"** для будущих обновлений (это более безопасно).

---

## Шаг 2: Проверка пакета перед загрузкой

```bash
python -m pip install -U twine
python -m twine check dist/*
```

Должно вывести: `PASSED`

---

## Шаг 3: Тестовая публикация на TestPyPI (РЕКОМЕНДУЕТСЯ)

### 3.1. Создайте токен на TestPyPI:
- Зарегистрируйтесь/войдите на https://test.pypi.org/account/register/
- Создайте API токен (аналогично основному PyPI)

### 3.2. Загрузите на TestPyPI:
```bash
python -m twine upload --repository testpypi dist/*
```

При запросе:
- **Username**: `__token__`
- **Password**: ваш токен с TestPyPI (начинается с `pypi-`)

### 3.3. Проверьте установку с TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ --no-deps ghost-protocol
ghost --help
```

---

## Шаг 4: Публикация на основной PyPI

```bash
python -m twine upload dist/*
```

При запросе:
- **Username**: `__token__`
- **Password**: ваш токен с основного PyPI (начинается с `pypi-`)

---

## Шаг 5: Проверка установки

Подождите 2-5 минут после загрузки, затем:

```bash
pip install ghost-protocol
ghost --help
ghost --install
```

---

## Команды для Windows (полный чеклист):

```bash
# 1. Убедитесь, что пакет собран
python -m build

# 2. Установите/обновите twine
python -m pip install -U twine

# 3. Проверьте пакет
python -m twine check dist/*

# 4. Загрузите на PyPI (сначала TestPyPI для теста)
python -m twine upload --repository testpypi dist/*
# или сразу на основной PyPI:
python -m twine upload dist/*

# 5. После загрузки проверьте установку
pip install ghost-protocol
ghost --help
```

---

## Важные замечания:

1. **Имя пакета**: `ghost-protocol` (с дефисом)
   - Команда установки: `pip install ghost-protocol`
   - Команда в терминале: `ghost` (без дефиса)

2. **Токен для первой публикации**: Используйте "Entire account" scope, так как проект еще не существует на PyPI. После публикации можно создать новый токен с ограничением "Project: ghost-protocol" для будущих обновлений.

3. **После публикации** версию нельзя изменить. Для обновления нужно изменить версию в `pyproject.toml` и пересобрать.

4. **Проверка доступности имени**: https://pypi.org/project/ghost-protocol/
   - Если страница не существует или показывает 404 - имя свободно
   - Если есть страница - имя занято (но вы можете загрузить новую версию, если это ваш проект)

---

## Если что-то пошло не так:

- **Ошибка "File already exists"**: Версия уже опубликована, нужно изменить версию
- **Ошибка "Invalid credentials"**: Проверьте, что используете `__token__` как username и правильный токен
- **Ошибка "Package name already taken"**: Имя занято, нужно выбрать другое

