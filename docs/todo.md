# TorrentFlow — Backlog / Ideas / TODO

Отдельный список идей и фич, которые стоит рассмотреть.  
Не входят в базовый scope v1 из IMPLEMENTATION.md, но реально полезны.

---

## Выполнено в текущем MVP

- [x] **Smart Auto-Add Rules**
  `auto_add` и `both` работают с min seeds, freeleech, double upload и максимальным размером.

- [x] **Uploader whitelist / blacklist**
  CSV allow/block lists сравниваются без учёта регистра; block list имеет приоритет.

- [x] **Freeleech / Double Upload detection**
  TorrentLeech adapter нормализует uploader, freeleech, double-upload и размер для matching.

- [x] **qb_category + save_path mapping** в правиле
  Smart rule передаёт `category` и `savepath` в qBittorrent при auto-add.

- [x] **Proxy / SOCKS5 support per feed**
  Поддерживаются HTTP(S), SOCKS5 и SOCKS5H proxy URL; proxy назначается конкретному feed.

- [x] **Disk space monitoring + alerts**
  Проверяется data volume, статус виден в health/Settings, audit и Telegram отправляются при смене состояния.

- [x] **Export / Import persisted config** (feeds + rules + categories + disk setting)
  JSON/YAML export и import; UI делает безопасный merge, API replace требует явного подтверждения.

---

## Высокий приоритет — закрыть до расширения доступа

- [x] **Запретить proxy credentials в SQLite и export**
  `user:password@` отклоняется общим валидатором, а migration `20260826_10` удаляет legacy URL с userinfo.

- [x] **Защищённые tracker credentials**
  Cookie/passkey хранятся write-only с Fernet-шифрованием, ключ поступает только из `TORRENTFLOW_ENCRYPTION_KEY`, а export/import их исключает.

- [x] **Добавить adapter integration suite**
  Есть local HTTP RSS/TorrentLeech fixture, реальный SOCKS5 transport и migration/startup coverage.

- [x] **Валидировать adapter type при создании feed**
  Pydantic contract принимает только поддерживаемые adapter types и возвращает `422` до сохранения.

- [x] **Явный policy для runtime settings**
  Portable export переносит disk threshold; credentials, URLs с userinfo и environment configuration не переносятся.

---

## Средний приоритет (v1.1)

- [x] **guessit + базовый парсинг названий**
  Release names получают безопасные series/movie labels и persistent group key; нераспознанные значения остаются исходными.

- [x] **Кастомные шаблоны Telegram-сообщений**
  Settings API принимает только whitelisted placeholders и применяет шаблон к release notifications.

- [x] **Поиск и advanced filters** в ленте релизов и History
  API поддерживает bounded search/filter/pagination для releases, audit и feed-run history по persisted полям.

- [ ] **API Token** для внешних интеграций  
  Home Assistant, n8n, скрипты и т.п.

- [ ] **MQTT events**  
  Полезно, если уже есть Home Assistant.

- [x] **Более детальный health / job log**
  Каждый scan сохраняет success/failure, duration, счётчики и безопасную классификацию ошибки.

---

## Низкий приоритет / Future

- [ ] Поддержка дополнительных трекеров через адаптеры (NexusPHP-based и др.)
- [ ] PWA-режим веб-панели
- [ ] Улучшенный mobile layout
- [ ] Возможность нескольких qBittorrent instances
- [ ] Базовые команды в Telegram-боте (/status, /latest, /check)
- [ ] Автоматический бэкап SQLite в shared folder по расписанию (UI-настройка)
- [ ] Rate-limit и retry policy per feed (более тонкая настройка)
- [ ] Cookie/session management для трекеров, где RSS требует логина

---

## Технический долг — выполнено

- [x] Нормальные миграции (Alembic) вместо `create_all`; runtime применяет `alembic upgrade head`.
- [x] Unit-тесты matching и HTTP-mock coverage qBittorrent/Telegram; полноценный adapter integration suite остаётся выше.
- [x] Multi-arch Docker build в CI для `linux/amd64` и `linux/arm64`.
- [x] Документация по деплою на Synology, включая named volumes и bind-mount permissions.

---

*Обновляй этот файл по мере принятия решений.*
