# TorrentFlow — Backlog / Ideas / TODO

Отдельный список идей и фич, которые стоит рассмотреть.  
Не входят в базовый scope v1 из IMPLEMENTATION.md, но реально полезны.

---

## Высокий приоритет (желательно в v1 или сразу после)

- [ ] **Smart Auto-Add Rules**  
  Отдельный action `auto_add` (или `both`) с условиями: freeleech only, min seeds, max size и т.д.  
  Сейчас в плане есть только notify + ручная кнопка.

- [ ] **Uploader whitelist / blacklist**  
  Фильтр по имени аплоадера. На TL это почти must-have.

- [ ] **Freeleech / Double Upload detection**  
  В адаптере TorrentLeech вытаскивать эти флаги и уметь фильтровать по ним.

- [ ] **qb_category + save_path mapping** в правиле  
  Чтобы разные типы релизов летели в разные категории/папки qB.

- [ ] **Proxy / SOCKS5 support per feed**  
  Многие ходят на трекеры через VPN/прокси. Нужна поддержка на уровне адаптера.

- [ ] **Disk space monitoring + alerts**  
  Следить за свободным местом на volume и слать уведомление при низком пороге.

- [ ] **Export / Import всего конфига** (feeds + rules + settings) в YAML/JSON  
  Чтобы можно было быстро восстановить после переустановки.

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

## Технический долг / Улучшения

- [ ] Нормальные миграции (Alembic) вместо create_all
- [ ] Шифрование cookies/passkey в БД
- [ ] Unit + integration тесты на адаптеры и matching
- [ ] Multi-arch Docker build в CI
- [ ] Документация по деплою на Synology (включая volume permissions)

---

*Обновляй этот файл по мере принятия решений.*
