# Test Suite

Эта папка содержит тестовые скрипты и результаты тестирования Ghost Protocol.

## Тестовые скрипты

### Основные тесты
- **`test_ghost_detection.py`** - Комплексный тест обнаружения и классификации файлов
- **`test_ghost_simple.py`** - Простой тест с git commit
- **`test_ai_review.py`** - Тест AI Review функциональности (CodeRabbit аналог)

### Аудит токенов
- **`audit_tokens.py`** - Аудит токенов проекта (базовый метод)
- **`audit_tokens_precise.py`** - Точный аудит токенов с использованием `tiktoken`
- **`compare_tokens.py`** - Сравнение результатов Ghost Protocol с аудит-скриптами

## Результаты тестирования

- **`TEST_RESULTS.md`** - Результаты тестирования файловой классификации
- **`AI_REVIEW_TEST_RESULTS.md`** - Результаты тестирования AI Review функциональности

## Использование

### Запуск тестов обнаружения файлов

```bash
# Простой тест
python test/test_ghost_simple.py

# Комплексный тест
python test/test_ghost_detection.py
```

**Важно**: Запусти Ghost Protocol в другом терминале перед тестами:
```bash
python main.py
```

### Запуск теста AI Review

```bash
python test/test_ai_review.py <project_path>
```

### Аудит токенов

```bash
# Базовый аудит
python test/audit_tokens.py <project_path>

# Точный аудит
python test/audit_tokens_precise.py <project_path>

# Сравнение с Ghost Protocol
python test/compare_tokens.py <project_path>
```

---

**Примечание**: Тесты требуют, чтобы Ghost Protocol был запущен в отдельном терминале, или используют моки для проверки логики.

