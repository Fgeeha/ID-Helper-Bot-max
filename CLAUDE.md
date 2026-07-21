# CLAUDE.md

Инструкции для Claude Code по этому репозиторию. Читай целиком перед началом
работы и держи в контексте на протяжении всей сессии.

## 0. ЗАПРЕТЫ В КОММИТАХ И ИСТОРИИ (жёстко, без исключений)

Эти правила имеют наивысший приоритет. Нарушение = откатить коммит.

- В сообщениях коммитов, в теле PR, в комментариях кода, в `CHANGELOG`, в авторстве
  и в любых артефактах репозитория **ЗАПРЕЩЕНО** упоминать: `Claude`, `Anthropic`,
  `claude.ai`, `claude code`, `AI`, `ИИ`, `сгенерировано`, `assistant`, `LLM`,
  «при помощи нейросети» и любые синонимы, прямо или косвенно указывающие на
  происхождение кода от ИИ-ассистента.
- **НЕ добавлять** трейлеры вида `Co-Authored-By: Claude ...`,
  `Generated with ...`, `🤖 ...` и подобные. Коммиты должны выглядеть как
  написанные человеком-разработчиком.
- **НЕ менять** `user.name` / `user.email` в git-конфиге. Использовать те, что
  уже настроены в окружении. Если они не настроены — остановиться и спросить.
- Сообщения коммитов — на русском, в стиле Conventional Commits
  (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`), по делу, без воды и эмодзи.
- Перед каждым `git commit` мысленно проверить тело и заголовок на наличие
  запрещённых слов. Если хоть одно есть — переписать.

---

## Что это за проект

Чат-бот для мессенджера **MAX** (платформа VK, `platform-api.max.ru`).
Бот показывает идентификаторы: `user_id` пользователя, `chat_id` чата,
ID автора пересланного сообщения и ID человека из пересланного контакта.

**Стек, который зафиксирован (не менять без явного запроса):**

- Python `>=3.12`
- Пакетный менеджер — **uv** (не pip, не poetry, не pipenv)
- Библиотека бота — **`maxapi`** (проверенный командой MAX форк,
  `pip install maxapi` / на GitHub `max-messenger/max-botapi-python`)
- Контейнеризация — Docker, **multi-stage** сборка на базе образов Astral uv
- Оркестрация — docker compose, два профиля: `local` и `prod`
- Автоматизация — Makefile

## Ключевые факты про MAX API (не выдумывай, сверяйся)

- Домен API: `https://platform-api.max.ru`. Старый `botapi.max.ru` устарел.
- Авторизация — токен в HTTP-заголовке `Authorization`. Передача токена в
  query-параметрах **не поддерживается**.
- Лимит запросов — 30 в секунду.
- Токен бота выдаёт системный бот **@MasterBot** (команда `/create`,
  ник обязан оканчиваться на `_bot`, 11–60 символов).
- Публикация ботов с августа 2025 — только для юрлиц РФ (верификация на
  dev.max.ru). На локальную разработку это не влияет.
- В групповых чатах боту нужны права администратора, иначе события не приходят.

### Библиотека `maxapi` — проверенные факты об API

Всё ниже сверено с реальным пакетом. Если сомневаешься — импортируй тип и
посмотри `.model_fields`, а не полагайся на память.

- Точки входа: `from maxapi import Bot, Dispatcher`.
- Роутеры: `from maxapi.dispatcher import Router`; `Router(router_id="...")`.
  Подключение: `dp.include_routers(r1, r2, ...)`.
- Декораторы событий: `@router.bot_started()`, `@router.message_created(...)`,
  `@router.message_callback()`.
- Фильтры команд: `from maxapi.types import Command, CommandStart`.
- Ответ на сообщение: `await event.message.answer(text=..., attachments=[...],
  parse_mode=ParseMode.HTML)`.
- Прямая отправка: `await bot.send_message(chat_id=..., text=..., ...)`.
- HTML-разметка: `from maxapi.enums.parse_mode import ParseMode` → `ParseMode.HTML`.
- Клавиатуры: `from maxapi.utils.inline_keyboard import InlineKeyboardBuilder`;
  методы `.row(...)`, `.add(...)`, `.adjust(...)`, `.as_markup()`.
  Кнопки: `CallbackButton(text, payload)`, `LinkButton(text, url)`,
  `ClipboardButton(text, payload)` (payload = текст в буфер),
  `RequestContactButton(text)`, `RequestGeoLocationButton(text)`.
- Модель `User`: поля `user_id, first_name, last_name, username, is_bot,
  last_activity_time, description, avatar_url, full_avatar_url, commands`.
- Пересланное сообщение: `event.message.link` (`LinkedMessage`) с полями
  `type, sender (User), chat_id, message`.
- Контакт как вложение: `attachment.type == "contact"`, полезная нагрузка
  `ContactAttachmentPayload(vcf_info, hash, max_info: User | None)` —
  `max_info.user_id` и есть ID нужного человека.
- Callback: `event.callback` (`Callback`) с полями `callback_id, payload, user`;
  подтверждать нажатие обязательно (`await event.answer()` или через `event.edit`),
  иначе кнопка «крутится».
- Polling: если раньше был вебхук — вызвать `await bot.delete_webhook()` перед
  `dp.start_polling(bot)`, иначе события не придут.
- Webhook-режим требует доп. зависимостей: `maxapi[webhook]` (fastapi + uvicorn).

## Структура репозитория

```
.
├── CLAUDE.md                     # этот файл
├── pyproject.toml                # метаданные + зависимости (uv)
├── uv.lock                       # лок-файл (коммитить!)
├── .env.example                  # шаблон переменных окружения
├── .dockerignore                 # ОБЯЗАТЕЛЬНО игнорирует .venv
├── Makefile                      # команды разработки и деплоя
├── docker/
│   ├── Dockerfile                # multi-stage: builder → runtime
│   ├── docker-compose.local.yml  # локальная разработка (watch/reload)
│   └── docker-compose.prod.yml   # прод (restart, лимиты, healthcheck)
└── src/
    └── bot/
        ├── __init__.py
        ├── __main__.py           # точка входа: сборка Dispatcher, polling
        ├── config.py             # чтение окружения (BOT_TOKEN, LOG_LEVEL...)
        ├── handlers/
        │   ├── __init__.py
        │   ├── ids.py            # логика извлечения ID
        │   └── callbacks.py      # обработка нажатий кнопок
        └── keyboards/
            ├── __init__.py
            └── menus.py          # inline-клавиатуры
```

Src-layout обязателен. Пакет — `bot`, запуск — `python -m bot`.

## Правила работы (для тебя, Claude Code)

1. **Зависимости — только через uv.** Добавить пакет: `uv add <pkg>`.
   Дев-зависимость: `uv add --dev <pkg>`. Никогда не редактируй список
   зависимостей в `pyproject.toml` руками и не запускай `pip install`.
   После любого изменения зависимостей убеждайся, что `uv.lock` обновлён и
   закоммичен.
2. **Не хардкодь секреты.** Токен и прочее — только из окружения через
   `config.py`. В коде и в compose-файлах секретов быть не должно; используй
   `.env` (он в `.gitignore`) и `.env.example` как шаблон.
3. **Проверяй перед сдачей.** Прежде чем сказать «готово», прогони:
   `make lint` и `make test` (или напрямую `uv run ruff check .`,
   `uv run pytest -q`). Не игнорируй красные тесты.
4. **Docker меняешь — проверь сборку.** После правок Dockerfile или compose
   собери образ (`make build`) и, если возможно, подними локальный стек.
5. **Сверяйся с библиотекой, а не с памятью.** Перед использованием
   незнакомого метода/поля `maxapi` — импортируй и посмотри реальную сигнатуру
   (`python -c "from maxapi.types import X; print(X.model_fields)"`).
6. **Минимальные диффы.** Меняй только то, что просят. Не переписывай рабочие
   модули «заодно», не меняй зафиксированный стек, не добавляй тяжёлых
   зависимостей без явной просьбы.
7. **Обновляй `.env.example` и README** при добавлении новой переменной
   окружения или новой make-команды.
8. **Комментарии и текст для пользователя — на русском**, имена в коде — на
   английском.

## Команды (Makefile)

- `make install` — `uv sync` (создать/обновить окружение из лок-файла)
- `make run` — локальный запуск бота без Docker (`uv run python -m bot`)
- `make lint` — `uv run ruff check .`
- `make fmt` — `uv run ruff format .`
- `make test` — `uv run pytest -q`
- `make build` — собрать Docker-образ
- `make up` / `make down` — поднять/остановить **локальный** стек
- `make logs` — логи локального стека
- `make prod-up` / `make prod-down` — прод-стек
- `make lock` — пересобрать `uv.lock` (`uv lock`)
- `make clean` — убрать кэши и артефакты

## Переменные окружения

| Переменная  | Обязательна | Назначение                              |
|-------------|-------------|-----------------------------------------|
| `BOT_TOKEN` | да          | Токен бота от @MasterBot                |
| `LOG_LEVEL` | нет         | Уровень логов (INFO по умолчанию)       |
| `ADMIN_IDS` | нет         | ID админов через запятую (для служебных команд) |

## Definition of Done

- Код проходит `make lint` и `make test`.
- Бот стартует локально (`make run`) и в Docker (`make up`).
- Нет секретов в коде и в истории git.
- `uv.lock` актуален и закоммичен.
- README и `.env.example` отражают текущее состояние.
- 