# EcoIQ: практический справочник Python, AI и DevOps

**Версия:** Python 3.11.16 — язык и версия проекта EcoIQ из .python-version. **Назначение:** обучение, проверка синтаксиса, тестируемые примеры, а не изменение production-ядра. Исходники находятся в examples/python_ai_devops. Примеры не выполняют deploy, не требуют API-ключей, не обращаются к клиентским данным и не предоставляют разрешение на бизнес-изменения.

## 1. Все ключевые слова Python 3.11

Всего 35 жёстких ключевых слов:

False, None, True, and, as, assert, async, await, break, class, continue, def, del, elif, else, except, finally, for, from, global, if, import, in, is, lambda, nonlocal, not, or, pass, raise, return, try, while, with, yield.

Мягкие ключевые слова: match, case, _ (шаблон wildcard, в соответствующем контексте). В Python 3.12 также добавилось особое использование type для type-alias statements; в версии EcoIQ 3.11 этот синтаксис не используется. Слова print, self, cls, len, int, list — не ключевые слова.

Проверка ключевых слов установленного интерпретатора: python -c "import keyword; print(keyword.kwlist); print(keyword.softkwlist)".

## 2. Все основные операторы

| Группа | Операторы | Пример |
|---|---|---|
| Арифметические | +, -, *, /, //, %, ** | 7 / 3 ≈ 2.333; 7 // 3 = 2; 7 % 3 = 1; 7 ** 3 = 343 |
| Матричное произведение | @ | A @ B — для типов, реализующих __matmul__, например NumPy/torch |
| Унарные | +x, -x | -x меняет знак |
| Сравнения | ==, !=, <, <=, >, >= | 0 < x <= 100 |
| Простое присваивание | = | x = 10 |
| Выражение с присваиванием | := | if (n := len(items)) > 0: ... |
| Составные присваивания | +=, -=, *=, /=, //=, %=, **=, @=, &=, \|=, ^=, <<=, >>= | n += 2 |
| Логические | and, or, not | verified and permitted |
| Принадлежности | in, not in | "water" in resources |
| Тождественности | is, is not | value is None |
| Побитовые | &, \|, ^, ~, <<, >> | 7 & 3 == 3; 7 ^ 3 == 4; 7 << 1 == 14 |

Логика: and/or используют короткое вычисление и могут возвращать **сам операнд**, а не bool (например пустая строка or "fallback"). not даёт bool. Для исключающего ИЛИ двух булевых условий можно использовать a != b. Оператор ^ — побитовое XOR, для степени нужен **. Оператор ~7 равен -8.

В NumPy/pandas & и | обычно поэлементные, поэтому пишите (frame["x"] > 0) & (frame["y"] < 5), а не and. is сравнивает идентичность объекта; для сравнения чисел и строк применяйте ==. Исключение: value is None.

Приоритет операций требует внимания: скобки делают код яснее. Пример: -2**2 равно -4, потому что степень вычисляется перед унарным минусом; сравнения вычисляются прежде not/and/or.

## 3. Функции, параметры и аргументы

**Параметр** — объявленное имя при def, **аргумент** — переданное значение при вызове. Сигнатура:

    def analyse(case_id: str, /, quantity: float | None = None,
                *, unit: str = "kg", **metadata: str) -> dict:
        if quantity is not None and quantity < 0:
            raise ValueError("Non-negative quantity expected")
        return {"case_id": case_id, "value": quantity, "unit": unit, "metadata": metadata}

    analyse("DEMO-1", 120, unit="kg", source="synthetic")

Смысл:
- / — всё до него передаётся только позиционно.
- * — всё после него передаётся только по имени.
- *args собирает позиционные аргументы в tuple; **kwargs собирает именованные аргументы в dict.
- При вызове f(*sequence, **mapping) распаковывает последовательность и словарь.
- Значение по умолчанию назначается один раз при определении функции: не используйте изменяемые defaults, такие как items=[].
- return возвращает результат; yield создаёт генератор; lambda строит краткую функцию-выражение.
- Аннотации типов помогают IDE/mypy, но не заменяют runtime-валидацию.
- from __future__ import annotations, dataclass, ParamSpec, TypeVar и Callable полезны для больших Django-проектов.

Реальные запускаемые примеры: examples/python_ai_devops/syntax_gallery.py (сигнатуры, varargs, += и :=, все семейства операторов, match/case, dataclass, yield, декоратор, async def).

## 4. Остальные элементы синтаксиса, которые необходимо знать

Условия: if / elif / else. Циклы: for и while; управление: break, continue, pass. Исключения: try / except / else / finally, raise, assert (для внутренней отладки, не для защиты данных). Контекстный менеджер with безопасно закрывает файлы и ресурсы.

Коллекции: list, tuple, dict, set, frozenset. Готовые выражения: [x*x for x in xs if x >= 0] (list comprehension), {x for x in xs} (set comprehension), {k: v for k, v in items} (dict comprehension), (x*x for x in xs) (generator expression).

Классы: class, наследование, super(), @property, @classmethod, @staticmethod, @dataclass. Асинхронные операции: async def, await, async for, async with — для I/O, а не как замена GPU при тренировке сети. Импортируйте через import и from ... import ..., используйте виртуальную среду. Для секретов и пользовательских документов не применяйте eval или exec.

## 5. Анализ данных без подмены доказательств

Существующие компоненты EcoIQ: ecoiq_os.process_csv.diagnose_csv и ecoiq_os.decision_islah.build_preliminary_brief. Лаборатория process_pipeline.py **повторно использует их**, не создаёт ещё один процессор бизнес-данных.

Цепочка: synthetic CSV → валидация чисел, единиц, периода и доказательств → reported KPI → статус COLLECT_EVIDENCE → гипотезы UNTESTED → человек.

Синтетический пример: 1000 кг поступления и 120 кг зафиксированных потерь → 12% **заявленных**, но не независимо подтверждённых потерь. Это не доказательство устранимых потерь, причинности, экономии или религиозного заключения.

Обязательные правила: None ≠ 0; NaN/inf и отрицательные величины запрещены; неизвестные данные не суммируются как будто нули. Для денег используйте decimal.Decimal. mean/median/std описывают выборку, но не доказывают причину. pandas/NumPy применяйте после валидации, учитывайте временную последовательность, источники данных и разделение train/validation/test. Для диаграмм используйте matplotlib/plotly в отдельном слое.

## 6. Нейронные сети и генеративные модели

В EcoIQ уже существуют ml/, ai_gateway/, agent_training_evaluation_lab/, requirements-neural.txt и requirements-training.txt. Не создавайте параллельный production AI-стек.

Учебный файл examples/python_ai_devops/torch_lab.py:
- train_tiny_regression: PyTorch Linear → Tanh → Linear, MSELoss, Adam, backward, optimizer step и no_grad на вымышленных числах y=2x+1.
- train_tiny_character_generator: Embedding → GRU → Linear, cross-entropy, backpropagation, clip_grad_norm, авторегрессионная генерация символов на искусственном тексте "eco iq".

Это действительно обучаемые модели, но **не LLM и не полноценный инструмент AI Decision & Islah**. Они не подключены к данным, API, клиентам или решениям. Для генеративных моделей с корпоративными документами необходимы: проверка права доступа при retrieval, контроль промптов, output schema, версионирование, тестовые датасеты, защита секретов, лимиты стоимости, трассировка и ручное согласование. Для retrieval-augmented generation сначала нужен авторизованный поиск подтверждённых источников.

## 7. DevOps и тестирование

Среда: Python 3.11.16 из .python-version, отдельная virtualenv, зависимости согласно requirements-dev.txt, отдельная установка PyTorch только при необходимости.

Безопасные команды:

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    bash scripts/dev/verify_python_ai_examples.sh
    bash scripts/dev/verify_python_ai_examples.sh --django
    bash scripts/dev/verify_python_ai_examples.sh --full

Опции: без флага — compileall, unittest и ruff при наличии; --django — дополнительно проверки Django, миграций и узкого API; --full — весь Django suite. Скрипт НЕ вызывает deploy, migrate, shell-команды cloud-сервиса или реальные внешние AI API.

.github/workflows/python-ai-kit.yml запускает изолированные smoke-тесты по PR на нужных ветках. PyTorch-тесты пропускаются, если библиотека не установлена, чтобы не раздувать web CI. Отдельно для реального деплоя обязательны staging DB, миграционный dry-run, synthetic E2E, проверка CSRF/RBAC, backup и rollback.

## 8. Диагностика Python

- python --version — версия.
- help(str), dir(obj), type(obj), isinstance(obj, cls) — изучение и проверка объектов.
- inspect.signature(fn), inspect.getsource(fn) — сигнатура и исходный код.
- python -m compileall -q path — проверка синтаксиса.
- python -m unittest ... и python manage.py test ... — тестирование.
- ruff check . и python -m mypy ... — анализ кода.
- python -m pdb script.py или breakpoint() — отладка.
- python -m cProfile -s cumtime script.py — профилирование CPU.
- python -m pip check — совместимость зависимостей.

## 9. Что действительно требуется EcoIQ для мирового рынка

Не существует технической задачи "добавить все операторы Python": они уже встроены в язык и не нужны в каждом модуле. Существенные пробелы определяются требованиями к конкретной функции: verified provenance, tenant isolation, защита данных, работающая CI, доверенные AI-выводы, проверяемые KPI, мониторинг и журнал согласований. Их следует внедрять отдельными тестируемыми PR.

**Контракт этой лаборатории:** никаких клиентских данных, никаких заявлений о причинности, никакой автоматической модификации бизнес-процессов.
