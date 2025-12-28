# 🔧 Быстрое решение: команда ghost не работает

## Проблема

Скрипт `ghost.exe` не был создан при установке пакета.

## ✅ Решение: Используйте Python напрямую

Вместо команды `ghost` используйте:

```powershell
# Установка hook
python -m main --install

# Запуск фонового режима
python -m main --ghost

# Монитор
python -m main --monitor
```

**НО:** Это работает только если вы находитесь в папке проекта Ghost Protocol.

## ✅ Правильное решение: Переустановите пакет

### Шаг 1: Удалите старую установку

```powershell
pip uninstall ghost-protocol -y
```

### Шаг 2: Переустановите

```powershell
pip install ghost-protocol
```

### Шаг 3: Проверьте, создались ли скрипты

```powershell
# Найдите папку Scripts
python -c "import site; import os; scripts = os.path.join(site.getuserbase(), 'Scripts'); print(scripts); print(os.path.exists(scripts))"
```

### Шаг 4: Если папка Scripts существует, добавьте в PATH

```powershell
# Получите путь
$scriptsPath = python -c "import site; import os; print(os.path.join(site.getuserbase(), 'Scripts'))"

# Добавьте в PATH (временно)
$env:Path += ";$scriptsPath"

# Проверьте
ghost --help
```

### Шаг 5: Добавьте в PATH постоянно

```powershell
# Получите путь
$scriptsPath = python -c "import site; import os; print(os.path.join(site.getuserbase(), 'Scripts'))"

# Добавьте в PATH постоянно (требует прав администратора)
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$scriptsPath", "User")
```

**Перезапустите PowerShell после этого!**

---

## 🔍 Альтернатива: Проверьте установку

Если скрипты все еще не создаются, возможно проблема в конфигурации пакета. В этом случае используйте:

```powershell
# Перейдите в папку проекта Ghost Protocol
cd "C:\Users\Antaras\Downloads\Ghost Protocol"

# Используйте напрямую
python main.py --install
python main.py --ghost
python main.py --monitor
```

---

## 📝 Временное решение для вашего проекта

Если вы хотите использовать Ghost Protocol в другом проекте (например, FaberlicFamilyBot), вы можете:

1. **Скопировать main.py и папку src** в ваш проект
2. **Или использовать через Python:**

```powershell
# В корне вашего проекта (FaberlicFamilyBot)
python -c "import sys; sys.path.insert(0, r'C:\Users\Antaras\Downloads\Ghost Protocol'); from main import main; import sys; sys.argv = ['main.py', '--install']; main()"
```

Но лучше всего - исправить установку пакета, чтобы команда `ghost` работала глобально.

