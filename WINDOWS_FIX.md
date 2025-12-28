# 🔧 Решение проблемы: команда `ghost` не найдена в Windows

## Проблема

После установки `pip install ghost-protocol` команда `ghost` не работает, потому что папка со скриптами Python не добавлена в PATH.

## ✅ Решение 1: Добавить Scripts в PATH (рекомендуется)

### Шаг 1: Найдите путь к Scripts

Выполните в PowerShell:
```powershell
python -c "import site; import os; print(os.path.join(site.getuserbase(), 'Scripts'))"
```

Обычно это: `C:\Users\ВашеИмя\AppData\Roaming\Python\Python314\Scripts`

### Шаг 2: Добавьте путь в PATH

**Вариант A: Через PowerShell (временно, до перезагрузки):**
```powershell
$env:Path += ";C:\Users\Antaras\AppData\Roaming\Python\Python314\Scripts"
```

**Вариант B: Постоянно через настройки Windows:**

1. Нажмите `Win + R`, введите `sysdm.cpl`, нажмите Enter
2. Перейдите на вкладку **"Дополнительно"**
3. Нажмите **"Переменные среды"**
4. В разделе **"Переменные пользователя"** найдите `Path`
5. Нажмите **"Изменить"**
6. Нажмите **"Создать"** и добавьте путь:
   ```
   C:\Users\Antaras\AppData\Roaming\Python\Python314\Scripts
   ```
7. Нажмите **"ОК"** во всех окнах
8. **Перезапустите PowerShell/терминал**

### Шаг 3: Проверьте

```powershell
ghost --help
```

---

## ✅ Решение 2: Использовать полный путь (быстро, но неудобно)

```powershell
& "C:\Users\Antaras\AppData\Roaming\Python\Python314\Scripts\ghost.exe" --install
```

---

## ✅ Решение 3: Использовать python -m (альтернатива)

Если entry point настроен правильно, можно попробовать:
```powershell
python -m ghost --install
```

Но это может не сработать, так как модуль называется `main`.

---

## ✅ Решение 4: Переустановить с правильным путем

```powershell
# Удалите старую установку
pip uninstall ghost-protocol

# Добавьте Scripts в PATH (временно)
$env:Path += ";C:\Users\Antaras\AppData\Roaming\Python\Python314\Scripts"

# Переустановите
pip install ghost-protocol

# Проверьте
ghost --help
```

---

## 🎯 Рекомендация

**Используйте Решение 1 (Вариант B)** - добавьте Scripts в PATH постоянно. Это решит проблему для всех Python-пакетов, которые устанавливают команды.

После добавления в PATH перезапустите терминал и команда `ghost` будет работать!

---

## 📝 Быстрая проверка после исправления

```powershell
# 1. Установите hook
ghost --install

# 2. Запустите фоновый режим
ghost --ghost

# 3. Проверьте монитор (в другом терминале)
ghost --monitor
```

