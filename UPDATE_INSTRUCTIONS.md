# 🔄 Обновление до версии 1.0.1

## Проблема

Если вы видите ошибку:
```
SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position 0-2: truncated \xXX escape
```

Это означает, что у вас установлена старая версия 1.0.0 с багом.

## ✅ Решение: Обновите пакет

```powershell
pip install --upgrade ghost-protocol
```

После обновления проверьте версию:
```powershell
pip show ghost-protocol
```

Должно показать: `Version: 1.0.1`

## Проверка работы

После обновления попробуйте:

```powershell
ghost --help
```

Или, если команда `ghost` не работает:

```powershell
python -m src --help
```

## Что было исправлено в версии 1.0.1

- ✅ Исправлена синтаксическая ошибка в `src/scanner.py` (`'\x0'` → `'\x00'`)
- ✅ Добавлена поддержка `python -m src` для Windows пользователей
- ✅ Обновлена документация с инструкциями для Windows

---

**Если ошибка все еще появляется после обновления:**

1. Полностью удалите пакет:
   ```powershell
   pip uninstall ghost-protocol -y
   ```

2. Переустановите:
   ```powershell
   pip install ghost-protocol
   ```

3. Проверьте версию:
   ```powershell
   pip show ghost-protocol
   ```

