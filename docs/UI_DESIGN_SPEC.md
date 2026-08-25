# TorrentFlow — UI design specification

## Design decision

**Subject:** a LAN-only control room for the person who wants RSS automation to be observable, safe and quick to correct.

**Audience:** one technical NAS owner, usually working at a desktop but occasionally checking the system from a phone.

**Single job:** make it immediately clear whether feeds, rules, qBittorrent and notifications are healthy — then provide the next safe action.

TorrentFlow uses the approved **Obsidian Flux** direction. The visual signature is a *flow line*: the cyan-to-blue throughput line appears as the active-download indicator, live chart trace and focus accent. It represents a release moving from feed to qBittorrent without resorting to decorative sci-fi noise.

## Foundations

| Role | Token |
| --- | --- |
| Canvas | `#10131b` |
| Deep inset | `#0b0e16` |
| Raised surface | `#1c2028` |
| Strong surface | `#272a32` |
| Primary / keyboard focus | `#adc6ff` |
| Live flow / positive action | `#00f4fe` |
| Warning / manual attention | `#ffb4a2` |
| Error | `#ffb4ab` |
| Primary text | `#e0e2ed` |
| Secondary text | `#c1c6d7` |
| Divider | `#414755` |

- **Type:** Inter for reading and hierarchy; JetBrains Mono only for labels, IDs, speeds, timestamps and statuses.
- **Density:** desktop uses an 8 px rhythm, 24 px card padding and 16 px inter-card gaps. Dense data views must still preserve a 44 px target for touch-capable controls.
- **Surfaces:** blur is reserved for the persistent navigation, app bar, popovers and the primary dashboard health card. Tables and long lists use solid raised surfaces to stay legible.
- **Icons:** Lucide, 20 px outline by default; selected navigation icon may be filled. Every icon-only control has an accessible label.
- **Motion:** 160–220 ms opacity/border-color transitions; live charts animate only when updates exist and expose a Pause control. `prefers-reduced-motion` renders a static latest state.

## Navigation

Desktop uses an 80 px icon rail with tooltips and an explicit current-page marker. The order reflects the operational flow, not an arbitrary menu:

`Dashboard → Feeds → Releases → Rules → Downloads → History → Notifications → Settings`

Mobile reduces this to five destinations: Dashboard, Releases, Downloads, Notifications and More. More opens the remaining three destinations; no critical operation depends on hover.

## Dashboard

The dashboard is a diagnostic surface, not a generic storage admin page.

1. **Health ribbon** — four compact source chips: RSS, Rules, qBittorrent, Telegram. Each exposes `Healthy`, `Degraded`, `Offline` or `Needs setup`, a last-updated time and a clear text status in addition to color.
2. **Flow card** — the largest card. It answers “what happened in the last 24h?”: releases discovered, matched, queued to qB and failed. A single flow line connects the stages; selecting a stage filters the recent-event list.
3. **Bandwidth card** — download/upload line chart, latest values, 1h/24h selector and Pause live updates. The chart has direct series labels and an accessible table fallback.
4. **Recent matches** — title, source, matched rule, size, seeds, outcome and a safe action. `Add to qB` appears only for `notify` rules; already-added rows display an immutable outcome badge.
5. **Attention queue** — only items needing a human: failed qB add, unhealthy feed, low disk or unconfigured Telegram. Empty state: “Nothing needs attention.”

## Screen contracts

| Screen | Primary decision | Essential content | Primary action |
| --- | --- | --- | --- |
| RSS Feeds | Is the source trusted and current? | status, next run, last success/error, interval | Add feed / Check now |
| Releases | Which release should be acted on? | filterable source, title, metadata, rule explanation, outcome | Add to qB |
| Rules | Why will a release be acted on? | ordered rule list, mode, conditions, matched count | Create rule |
| Downloads | Is qB currently progressing safely? | active torrents, speed, ETA, progress, qB status | Open in qB |
| History | What changed over time? | aggregates, range filter, category/source breakdown | Export CSV |
| Notifications | Did an alert reach its destination? | event type, delivery state, timestamp, retry reason | Test Telegram |
| Settings | Are access, secrets and backups correct? | connection test states, token controls, backup status | Save changes |

## States and safeguards

- Every list has loading skeletons, a specific empty state and an error state that explains the next action.
- Dangerous actions require confirmation: delete a feed/rule and Check all now. `Add to qB` gives immediate toast feedback and writes an audit event.
- Forms keep values on failure, show inline errors near each field and permit password managers/paste.
- Keyboard order follows the visual order. Focus is a 2 px `#adc6ff` ring with sufficient offset and is never hidden by the fixed header or mobile navigation.
- Use text, icon and color for statuses; never color alone.

## Design acceptance criteria

The UI phase is approved when the eight screen contracts above have desktop and mobile layouts, including empty, loading, error and degraded-source states, and when a user can follow this path without help:

`Add feed → test connection → create notify rule → inspect matched release → add to qB → see notification and audit record.`
