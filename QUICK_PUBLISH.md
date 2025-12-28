# 🚀 Быстрая публикация Ghost-Protocol на PyPI

## ✅ Что уже готово:
- ✅ Пакет собран (`dist/` содержит файлы)
- ✅ `pyproject.toml` настроен
- ✅ Название пакета: `ghost-protocol`
- ✅ Версия: `1.0.0`
- ✅ Команда `ghost` зарегистрирована

---

## 📋 Пошаговая инструкция:

### Шаг 1: Установите twine

```bash
python -m pip install -U twine
```

### Шаг 2: Создайте API токен на PyPI

1. Откройте https://pypi.org/account/login/ и войдите
2. Перейдите: **Account settings** → **API tokens** → **Add API token**
3. Заполните:
   - **Token name**: `ghost-protocol-upload`
   - **Scope**: **"Entire account"** (для первой публикации)
   - **Expiration**: Выберите срок или "No expiration"
4. Нажмите **"Add token"**
5. **ВАЖНО**: Скопируйте токен сразу! Он начинается с `pypi-` и показывается только один раз
6. Сохраните токен в безопасном месте

### Шаг 3: Проверьте пакет перед загрузкой

```bash
python -m twine check dist/*
```

Должно вывести: `PASSED`

### Шаг 4: Загрузите на PyPI

```bash
python -m twine upload dist/*
```

**При запросе:**
- **Username**: `__token__`
- **Password**: ваш токен (весь, включая префикс `pypi-`)

### Шаг 5: Проверьте установку

Подождите 2-5 минут после загрузки, затем:

```bash
pip install ghost-protocol
ghost --help
```

---

## 🎯 После публикации:

1. Проект будет доступен на: https://pypi.org/project/ghost-protocol/
2. Можно создать ограниченный токен "Project: ghost-protocol" для будущих обновлений
3. Команда `pip install ghost-protocol` будет работать для всех

---

## ⚠️ Если возникнут ошибки:

- **"File already exists"**: Версия уже опубликована, измените версию в `pyproject.toml`
- **"Invalid credentials"**: Проверьте, что используете `__token__` как username
- **"Package name already taken"**: Имя занято (но это ваш проект, так что просто обновите версию)

---

## 📝 Команда будет работать так:

```bash
# Установка
pip install ghost-protocol

# Использование
ghost --install
ghost --ghost
ghost --monitor
```

