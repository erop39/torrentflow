# TorrentFlow — NAS-first RSS Torrent Tracker

> Docker-сервис для Synology DS224+ (и любого другого NAS), который 24/7 мониторит TorrentLeech + любые RSS/Atom, применяет правила, шлёт уведомления и показывает красивую тёмную панель + Windows tray-клиент.

**Статус:** Implementation Plan v1.0  
**Целевая платформа:** Synology DS224+ (ARM64) + Windows tray  
**Основной стиль UI:** тёмный dashboard в духе современных Stitch / shadcn dark admin panels (высокая плотность, аккуратные карточки, боковая навигация, акцент на статус и цифры)

---

## 1. Видение и цели

**Зачем это вообще нужно**

Большинство RSS-to-qB решений либо слишком тупые (просто кидают всё подряд), либо перегружены (FlexGet + куча YAML-адов), либо не живут 24/7 на NAS и не имеют нормального UI. TorrentFlow должен быть:

- Всегда запущен на NAS (не зависит от включённого ПК)
- Иметь нормальный тёмный веб-интерфейс + лёгкий Windows tray
- Уметь и уведомлять, и (по желанию) автоматически добавлять
- Хранить полную историю и статистику
- Легко расширяться новыми трекерами через адаптеры

**Non-goals v1**

- Управление qBittorrent (пауза, удаление, приоритеты, выбор файлов) — только мониторинг
- Внешний доступ из интернета (только LAN + опциональный reverse proxy позже)
- Импорт из старых TL Notifier / YAML
- Мультипользовательский режим

---

## 2. Tech Stack (конкретный)

| Слой              | Выбор                                      | Почему |
|-------------------|--------------------------------------------|--------|
| Backend           | FastAPI + SQLModel + asyncio               | Быстро, типизация, отличный OpenAPI |
| Background tasks  | APScheduler (или встроенный FastAPI lifespan + asyncio tasks) | Проще Celery для одного контейнера |
| DB                | SQLite + WAL + aiosqlite                   | Идеально для NAS, один файл, бэкапы простые |
| Frontend          | React 19 + Vite + TypeScript + Tailwind + shadcn/ui | Современный тёмный dashboard, легко кастомизировать |
| Auth              | Простая session + bcrypt (один admin)      | Хватит для LAN |
| Realtime          | WebSocket + fallback polling               | Для tray и живых обновлений |
| Docker            | multi-arch (linux/arm64 + linux/amd64)     | DS224+ + обычные ПК |
| Tray client       | Python 3.12 + pystray + win10toast + requests | Лёгкий, без Electron |
| Telegram          | python-telegram-bot (или httpx)            | Стабильно |
| Parsing           | feedparser + guessit (для названий)        | Проверено годами |

---

## 3. Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose (NAS)                    │
│  ┌──────────────────────┐     ┌──────────────────────────┐  │
│  │  FastAPI + React     │◄───►│  SQLite (persistent)     │  │
│  │  (один контейнер)    │     │  volume                  │  │
│  └──────────┬───────────┘     └──────────────────────────┘  │
│             │                                               │
│             │  HTTP / WebSocket                             │
│             ▼                                               │
│  ┌──────────────────────┐                                   │
│  │  qBittorrent Web API │                                   │
│  └──────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
             ▲
             │ LAN only
             │
┌────────────┴────────────┐
│  Windows Tray Client    │
│  (иконка + toast)       │
└─────────────────────────┘
```

- Один контейнер = backend + собранный frontend (static files).
- Все секреты через env / docker secrets.
- Healthcheck + `/api/health`.
- Бэкап SQLite по расписанию в shared folder NAS.

---

## 4. Data Model (основные сущности)

```python
Feed
- id, name, url, adapter_type (torrentleech / generic_rss)
- enabled, last_check, last_success, last_error
- interval_minutes, headers, cookies (encrypted)
- created_at, updated_at

FilterRule
- id, name, enabled
- include_keywords, exclude_keywords (list)
- regex_include, regex_exclude
- min_size_mb, max_size_mb
- categories, trackers, uploaders_whitelist, uploaders_blacklist
- freeleech_only, min_seeds, max_leechers
- action: notify | auto_add | both
- qb_category, qb_save_path (опционально)
- priority

Release
- id, feed_id, external_id (hash/guid)
- title, size_bytes, category, uploader
- seeds, leechers, freeleech, double_upload
- published_at, first_seen_at
- download_url, info_url
- matched_rules (M2M)
- status: new / notified / added / ignored / error

QbTorrentSnapshot (периодические снимки)
- infohash, name, size, progress, dlspeed, upspeed
- eta, ratio, state, category, added_on, completed_on
- snapshot_at

DownloadEvent / NotificationEvent
- type, payload, created_at, seen

AppSettings / User
```

Дедупликация релизов идёт по `(feed_id + external_id)` + дополнительно по infohash, если удалось вытащить.

---

## 5. Публичный API (основные группы)

```
/api/auth          login / logout / me
/api/feeds         CRUD + check_now + enable/disable
/api/rules         CRUD + reorder
/api/releases      list + filters + send_to_qb
/api/downloads     current snapshots + history
/api/history       агрегаты + фильтры
/api/notifications list + mark_seen + test_telegram
/api/settings      get/update (в т.ч. telegram, qb url/creds, intervals)
/api/health        status, disk, last_jobs
/ws                realtime events (new_release, download_complete, feed_error...)
```

Все эндпоинты под JWT/session. Tray-клиент использует тот же API + long-polling/WebSocket.

---

## 6. Core Behavior

### RSS / Адаптеры
- Реестр адаптеров (`adapters/base.py` + `adapters/torrentleech.py` + `adapters/generic.py`)
- TorrentLeech: поддержка passkey-URL, парсинг категории, freeleech, размера, сидов (если есть в фиде)
- Generic RSS/Atom: максимально толерантный парсер
- Экспоненциальный backoff + per-feed rate limit
- Возможность указать custom headers / cookies

### Правила
- Два режима: `notify` и `auto_add` (можно оба)
- Поддержка regex, uploader white/black list, freeleech_only, min/max size, min seeds
- При auto_add можно задать qb_category и save_path

### qBittorrent
- Только чтение (WebAPI)
- Периодические snapshots → строим графики скорости и историю без нагрузки на qB
- Показ активных / завершённых, ошибок, ratio

### Dashboard
- Карточки: активные фиды, новые релизы (24ч), активные загрузки, место на диске, telegram-события
- Последние релизы + активные торренты
- Мини-график download/upload за выбранный период

### History
- Полная история + фильтры + агрегаты «скачано за месяц / по категориям»

### Telegram
- События: matched release, download finished, feed/qB down, low disk
- Тестовое сообщение + отдельные тумблеры
- Красивые сообщения с кнопками (открыть в панели / добавить вручную)

### Надёжность
- Дедуп, журнал задач, health endpoint
- Автобэкап SQLite + экспорт/импорт настроек (JSON/YAML)

---

## 7. UI Structure (тёмный Stitch-style)

Боковая навигация:
- Dashboard
- RSS Feeds
- Releases (лента)
- Rules
- Downloads (активные)
- History
- Notifications
- Settings

Верхняя строка: поиск + статус соединения с qB + колокольчик.

Карточки с акцентными цветами статуса (зелёный — ок, жёлтый — warning, красный — error). Высокая плотность, минимум воздуха, как в хороших admin-панелях.

---

## 8. Windows Tray Client

- Иконка в трее (меняется цвет/статус)
- Badge с количеством непрочитанных событий
- Toast-уведомления (Windows native)
- Контекстное меню:
  - Открыть панель
  - Последние релизы
  - Активные загрузки
  - Проверить сейчас
  - Выход
- Подключается только к NAS по LAN (настраиваемый URL + токен)
- Минимальный footprint

---

## 9. Roadmap по фазам

**Phase 0 — Skeleton (1–2 дня)**
- Docker multi-arch + FastAPI + SQLite + базовый auth
- Пустой React + Tailwind + shadcn dark theme
- Health endpoint

**Phase 1 — Core Backend**
- Модели + миграции
- Адаптеры TL + generic
- Фоновые задачи проверки фидов
- Правила + matching
- Интеграция qB (snapshots)
- Telegram

**Phase 2 — Web UI**
- Все основные экраны
- Realtime через WebSocket
- Ручная отправка в qB

**Phase 3 — Tray Client**
- Python tray + toast + меню
- Подключение к API

**Phase 4 — Polish**
- Бэкапы, экспорт/импорт, health, тесты, документация
- Docker Compose пример под Synology

---

## 10. Test Plan

- Unit: адаптеры, нормализация размера, matching правил, дедуп
- Integration: mock RSS + mock qB + mock Telegram
- E2E UI: добавление фида → правило → релиз → отправка в qB
- Docker smoke на arm64 (через QEMU или реальный DS224+)
- Tray против mock API

---

## 11. Assumptions

- Чистый старт, без импорта старых данных
- NAS работает независимо от Windows
- qBittorrent только мониторится
- Только LAN в первой версии

---

## 12. Структура репозитория (предложение)

```
torrentflow/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── adapters/
│   │   ├── models/
│   │   ├── services/
│   │   ├── workers/
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   └── package.json
├── tray/
│   └── ...
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   └── IMPLEMENTATION.md   ← этот файл
└── README.md
```
