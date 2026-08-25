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

- [x] **Export / Import persisted config** (feeds + rules + categories)
  JSON export и JSON/YAML import; UI делает безопасный merge, API replace требует явного подтверждения.

---

## Высокий приоритет — закрыть до расширения доступа

- [ ] **Запретить proxy credentials в SQLite и export**
  Сейчас `user:password@` в proxy URL можно сохранить и выгрузить вместе с конфигурацией. Нужна валидация без userinfo или отдельное environment-only хранение.

- [ ] **Определить и реализовать модель защищённых tracker credentials**
  Сейчас passkey/cookies в БД не существуют: RSS URL и integration credentials не должны содержать секретов. Если tracker потребует cookie/passkey, добавить зашифрованное at-rest хранение с ротацией ключа, а не хранить значения в feed URL.

- [ ] **Добавить настоящий adapter integration suite**
  Нужны локальный HTTP RSS/TorrentLeech fixture, проверка SOCKS transport и migration/startup lifecycle; существующие тесты покрывают matching и HTTP-моки.

- [ ] **Валидировать adapter type при создании feed**
  Неверный adapter сейчас сохранится и упадёт при первом scan вместо `422`.

- [ ] **Расширить export/import до явного policy для runtime settings**
  Решить, какие non-secret settings (например, disk threshold) должны быть переносимы, сохранив credentials только в environment.

---

## Средний приоритет (v1.1)

- [ ] **guessit + базовый парсинг названий**  
  Красиво показывать Show S03E05, Movie (2024) и т.д. + возможность группировки.

- [ ] **Кастомные шаблоны Telegram-сообщений**  
  Чтобы можно было настроить текст уведомления под себя.

- [ ] **Поиск и advanced filters** в ленте релизов и History  
  По названию, uploader, категории, размеру, freeleech и т.д.

- [ ] **API Token** для внешних интеграций  
  Home Assistant, n8n, скрипты и т.п.

- [ ] **MQTT events**  
  Полезно, если уже есть Home Assistant.

- [ ] **Более детальный health / job log**  
  История последних проверок фидов, ошибки, время выполнения.

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
