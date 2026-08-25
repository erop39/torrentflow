# Frontend code review — 2026-08-23

## Scope and method

В рабочей папке нет Git-репозитория, поэтому review по diff от фиксированной точки выполнить невозможно. Проведён полный source review доступной frontend-базы: `docs/design/torrentflow_v2/index.html`, `docs/UI_DESIGN_SPEC.md` и новой реализации `frontend/`.

## Findings in the original prototype

| Severity | Finding | Impact | Resolution |
| --- | --- | --- | --- |
| High | Один HTML-файл смешивает разметку, состояния, данные и обработчики. | Любая новая функция увеличивает риск регрессии. | Создан компонентный React + TypeScript frontend. |
| High | Внешние Google Fonts и Lucide CDN. | LAN-first UI зависит от внешней сети и стороннего runtime. | Иконки перенесены в локальную npm-зависимость `lucide-react`; шрифты пока используют системный fallback. |
| High | Inline handlers и динамическая вставка строк HTML. | Нет типизации, сложнее тестировать, выше риск XSS при появлении серверных данных. | События перенесены в React handlers; данные описаны типами. |
| Medium | Макет строк опирается на количество DOM-узлов и CSS `:has`. | Изменение колонок могло перекрывать действия — это уже проявлялось. | У React-строки фиксирована явная сетка из шести колонок; mobile-разметка определена отдельно. |
| Medium | Нет модели доменных данных. | Невозможно безопасно подключить API и показать loading/error. | Добавлены типы `Page`, `Release`, `Toast`; следующий шаг — API-клиент и серверные состояния. |
| Medium | Нет production build и typecheck. | Ошибки обнаруживаются только в браузере. | Добавлены `npm run build` и строгая TypeScript-конфигурация. |

## Spec alignment

- Реализованы: 8 направлений навигации, Dashboard health ribbon, flow card, bandwidth card, recent matches, attention queue, поиск, responsive mobile navigation и текстовые статусы.
- Частично реализованы: все остальные экраны имеют рабочую навигацию и action feedback, но пока используют mock data.
- Ещё не реализованы: API, auth/session, CRUD-формы, loading/error states из сервера, WebSocket, подтверждения опасных действий, history filters и интеграции qBittorrent/Telegram.

## Verification

- `npm run build` — успешно: TypeScript typecheck и production Vite build.
- Desktop browser QA — Dashboard отрисовывается без ошибок консоли.
- Mobile QA прототипа — горизонтальный overflow устранён; это изменение отражено в `CHANGELOG.md`.

## Next implementation slice

Первый API-срез завершён: frontend подключён к `/api/health` и `/api/releases`, а loading/empty/error состояния добавлены. Следующий шаг — постоянное хранилище SQLite + Alembic и CRUD RSS-источников.
