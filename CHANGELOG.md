# Changelog

Все существенные изменения TorrentFlow фиксируются здесь. Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/); версии будут добавлены с началом реализации приложения.

## [Unreleased]

### Added

- Добавлен multi-arch GitHub Actions build для `linux/amd64` и `linux/arm64`: pull request проверяет сборку, а `main` и version tags публикуют backend/frontend images в GHCR.
- Добавлена подробная инструкция развёртывания на Synology Container Manager: GHCR images, managed volumes и bind mounts, права `root:root`/`0700`, backups, восстановление, upgrades, HTTPS и troubleshooting.
- Расширено backend-покрытие до 26 тестов: edge cases matching и изолированные HTTP-проверки qBittorrent/Telegram адаптеров.
- Добавлен persistent каталог категорий: в Settings можно создать категорию, назначить ей цвет и выбрать, показывать ли её по умолчанию; Releases по умолчанию скрывает неинтересные категории, а All categories временно раскрывает их.
- Экраны Downloads, History, Notifications и Settings подключены к существующим API: отображают loading/error/empty/unconfigured состояния, безопасные проверки qBittorrent/Telegram и persistent audit-данные без показа секретов.
- Добавлены Synology-ориентированный `docker-compose.yml`, Dockerfiles, Alembic-миграции при старте, health check backend и отдельный сервис консистентных rotating SQLite backups.
- Добавлены интеграционные проверки RSS → rule → qBittorrent/Telegram → audit и API интеграций.
- Исправлены production-блокеры из review: Alembic теперь использует runtime SQLite URL, readiness проверяет БД, production отвергает placeholder-учётные данные, frontend использует Nginx API proxy, а Docker build contexts исключают секреты и локальные данные.
- Усилены backups (валидация retention, уникальные имена, атомарное завершение, logging) и добавлены scheduler/failure тесты, изоляция тестовой SQLite БД и инструкция восстановления.
- Исправлена совместимость RSS scheduler с SQLite: legacy timestamps без timezone нормализуются к UTC, поэтому одна уже проверенная лента не прерывает весь scheduled scan.
- Добавлен корневой `README.md` с назначением TorrentFlow, локальным запуском, переменными окружения, проверками и roadmap.
- Добавлен Memory Bank в `memory-bank/` и указатели для Codex/Copilot (`AGENTS.md`, `.github/copilot-instructions.md`) с правилами чтения, обновления и исключения секретов.
- Добавлены автоматический scheduler RSS, seed-пороги и category/action (`notify`, `auto_add`, `both`) в pipeline правил; результаты и audit-события сохраняются в SQLite.
- Добавлены защищённые API-адаптеры qBittorrent и Telegram, endpoints проверки подключений, Downloads и журнал audit. Секреты читаются только из переменных окружения.
- В RSS feeds добавлено удаление источника с подтверждением; вместе с источником удаляются его сохранённые результаты сканирования.
- Экран Releases теперь читает persistent queue из SQLite: все результаты RSS-сканов видны по источнику, правилу, времени и итоговому решению.
- После `Check now` RSS feeds показывает сохраняемый результат сканирования: число проверенных и новых релизов, названия, применённое правило и итоговый статус.
- Экран Rules подключён к `/api/rules`: отображает сохранённые правила и создаёт новые с названием, ключевыми словами, минимальными сидами, действием и приоритетом.
- Добавлены persistent rules: модель SQLite, защищённые `/api/rules` list/create endpoints и Alembic migration `20260824_02`.
- Добавлен экран входа и рабочая UI-форма создания RSS feed, подключённая к защищённому API.
- Добавлен session-auth для единственного LAN-admin: `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`; releases и feeds API теперь требуют активную HttpOnly session.
- Добавлен Alembic baseline `20260824_01` для таблицы RSS feeds и конфигурация миграций.
- Добавлено SQLite-хранилище и первый persistent CRUD `/api/feeds`; экран RSS feeds читает список из API и показывает loading/empty состояния.
- Добавлен первый FastAPI-срез в `backend/`: типизированные `/api/health` и `/api/releases`, CORS для локальной разработки и contract-тесты.
- Dashboard теперь получает health и recent releases через API, показывая loading, empty и connection-error состояния вместо чистого mock-only поведения.
- Добавлен [frontend code review](docs/FRONTEND_REVIEW.md) с архитектурными находками, соответствием спецификации и следующими шагами.
- Добавлен `frontend/`: рабочая основа React + TypeScript + Vite с локальными зависимостями вместо CDN-прототипа.
- Реализован первый интерактивный вертикальный срез: Dashboard, навигация, поиск, toast-обратная связь, релизные действия и responsive layout.
- Dashboard Search is now interactive in the prototype: it searches releases, RSS feeds, rules and qBittorrent, supports Enter and Escape, and opens the matching screen.
- Утверждён UI-эталон: [интерактивный прототип](docs/design/torrentflow_v2/index.html) в стиле Obsidian Flux.
- Описана полная дизайн-система и контракты восьми экранов в [UI_DESIGN_SPEC.md](docs/UI_DESIGN_SPEC.md): Dashboard, RSS feeds, Releases, Rules, Downloads, History, Notifications и Settings.
- Добавлены состояния ready, empty, loading и error для основных экранов, а также модальные формы создания RSS-источника и правила.
- В Settings добавлено управление цветами категорий `series` и `linux`; цвет используется как дополнительный маркер релиза.
- В таблицах релизов добавлены цветной маркер перед названием и выделенная колонка категории.
- Во все основные действия добавлены единообразные иконки Lucide и интерактивная обратная связь.

### Changed

- API больше не создаёт SQLite-схему через `create_all`: при каждом старте применяется идемпотентный `alembic upgrade head`, поэтому local и production используют один versioned migration lifecycle.
- Аудит хранения подтвердил, что SQLite не содержит passkeys, cookies или integration credentials: session cookie хранит только подписанный признак admin, а все секреты остаются в environment variables.
- Удалён случайно закоммиченный Telegram token из design-прототипа и переписана Git history; token требует отзыва и перевыпуска в BotFather.
- Исправлены финальные QA-находки: mobile navigation теперь открывает все восемь экранов, custom category labels используют назначенный цвет, health отражает фактическую конфигурацию интеграций, rules валидируют action, а RSS URL отклоняют локальные/private и non-HTTP адреса.
- Обновлён Memory Bank: зафиксированы текущий API-клиент интеграций, незавершённые экраны и следующие release-задачи.
- Цвет маркера релиза снова зависит от сохранённой категории, а не от действия правила.
- Обновлена локальная SQLite-схема до Alembic revision `20260824_04` без удаления feeds, rules или release-данных: добавлены поля `releases.matched_rule_id` и `releases.status`, необходимые для проверки RSS.
- Исправлена отправка React-форм: `Sign in`, `Save feed` и `Save rule` теперь действительно вызывают соответствующие обработчики `onSubmit`.
- Исправлен CORS для browser-based session login и CRUD: разрешены `POST`, `PATCH` и `Content-Type` для локального Vite frontend.
- Экраны Rules, Downloads, History, Notifications и Settings больше не показывают центрированную заглушку: добавлены содержательные стартовые состояния, а карточки используют всю ширину рабочего canvas.
- Экран Releases приведён к контракту: убраны дубли заголовка, таблица растянута на доступную ширину, добавлены заголовки колонок и корректная иконка фильтров.
- Цветной маркер релиза перемещён в одну строку с названием; он больше не занимает отдельную строку над заголовком.
- React-кнопки и типографика выровнены с утверждённым прототипом: локальные Inter и JetBrains Mono, базовый текст 14 px, controls 13 px/600 и прежняя плотность кнопок.
- Монолитный HTML-прототип больше не является единственной frontend-базой: UI разделён на типизированные React-компоненты и доменные типы.
- Восстановлен единый вертикальный отступ 16 px между соседними карточками на экранах: диагностические и state-блоки больше не сливаются с основной карточкой.
- Устранён горизонтальный overflow на мобильном Dashboard: health-карточки и основные grid-блоки теперь сжимаются в пределах экрана, не выходя за край.
- Приведены к единому компактному виду кнопки действий (`Audit`, `Add to qB`, `Check now`, `Open in qB` и др.): одинаковая высота, иконка, отступы и состояние disabled.
- Статусные плашки (`Healthy`, `Active`, `Downloading` и др.) центрированы внутри своей колонки.
- Увеличен вертикальный интервал в карточке Attention queue между меткой, заголовком и описанием ошибки.
- Переработана сетка строк без категории: статус и кнопка действия закреплены в отдельных колонках. Длинные кнопки больше не перекрывают статус или данные; мобильная версия сохраняет отдельную колонку действия.
- Исправлено скрытие модального окна Create: закрытая модалка больше не остаётся поверх интерфейса.

### Planned

- Финальный UI QA восьми экранов на desktop и mobile.
- Перенос утверждённого прототипа в рабочий frontend.
- Реализация backend-интеграций: RSS/TorrentLeech, правила, qBittorrent, Telegram, аудит и настройки.
- Отдельная поздняя фаза: системный трей.
