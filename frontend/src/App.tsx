import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import {
  Bell, Check, Download, ExternalLink, Gauge, History, LayoutDashboard, ListFilter,
  Plus, RefreshCw, Rss, Search, Settings, SlidersHorizontal, Trash2, Waves, X,
} from 'lucide-react'
import type { Page, Release, Toast } from './types'
import { api } from './api'
import type { AuditEvent, Category, DiskStatus, DownloadItem, Feed, FeedCheckResult, IntegrationStatus, Rule, ServiceHealth } from './types'

const fallbackReleases: Release[] = [
]

const pages: Array<{ id: Page; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard }, { id: 'feeds', label: 'RSS feeds', icon: Rss },
  { id: 'releases', label: 'Releases', icon: ListFilter }, { id: 'rules', label: 'Rules', icon: SlidersHorizontal },
  { id: 'downloads', label: 'Downloads', icon: Download }, { id: 'history', label: 'History', icon: History },
  { id: 'notifications', label: 'Notifications', icon: Bell }, { id: 'settings', label: 'Settings', icon: Settings },
]

function Button({ children, onClick, primary = false, label, submit = false }: { children: React.ReactNode; onClick?: () => void; primary?: boolean; label?: string; submit?: boolean }) {
  return <button className={`btn${primary ? ' primary' : ''}`} type={submit || !onClick ? 'submit' : 'button'} onClick={onClick} aria-label={label}>{children}</button>
}

function Badge({ children, warning = false }: { children: React.ReactNode; warning?: boolean }) {
  return <span className={`badge${warning ? ' warning' : ''}`}>{children}</span>
}

function ReleaseRow({ release, addToast, categoryColor = '#ad8cff' }: { release: Release; addToast: (message: string) => void; categoryColor?: string }) {
  const isAdded = release.status === 'auto_add'
  const outcome = isAdded ? 'Auto-add' : release.status === 'notify' ? 'Notify' : 'Ignored'
  const category = release.category
  return <div className="data-row">
    <div className="release-name"><strong><i className={`release-marker ${category}`} style={{ backgroundColor: categoryColor, boxShadow: `0 0 9px ${categoryColor}` }} aria-hidden="true" />{release.title}</strong><small>{release.rule_name ? `Rule: ${release.rule_name}` : 'No matching rule'} · {category}</small></div>
    <span className="category-label">{release.source}</span><span>{release.rule_name ?? '—'}</span><span>{new Date(release.created_at).toLocaleString()}</span>
    <Badge warning={!isAdded}>{outcome}</Badge>
    <Button onClick={() => addToast(`${release.title}: ${outcome.toLowerCase()}`)}><Check /> Inspect</Button>
  </div>
}

function SearchDialog({ open, onClose, onGo, releases }: { open: boolean; onClose: () => void; onGo: (page: Page) => void; releases: Release[] }) {
  const [query, setQuery] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const matches = useMemo(() => {
    const index = [
      ...releases.map(r => ({ title: r.title, detail: `Release · ${r.status}`, page: 'releases' as Page })),
      { title: 'TorrentLeech', detail: 'RSS feed · healthy', page: 'feeds' as Page }, { title: 'Animation 4K', detail: 'Rule · auto-add', page: 'rules' as Page },
      { title: 'qBittorrent', detail: 'Connection · degraded', page: 'downloads' as Page },
    ]
    return index.filter(item => `${item.title} ${item.detail}`.toLowerCase().includes(query.toLowerCase()))
  }, [query])
  useEffect(() => { if (open) { setQuery(''); requestAnimationFrame(() => input.current?.focus()) } }, [open])
  useEffect(() => { const close = (event: KeyboardEvent) => event.key === 'Escape' && onClose(); window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close) }, [onClose])
  if (!open) return null
  return <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="search-dialog" role="dialog" aria-modal="true" aria-labelledby="search-title" onMouseDown={event => event.stopPropagation()}>
      <div className="dialog-heading"><div><span className="eyebrow">Quick search</span><h2 id="search-title">Find a release, feed or rule</h2></div><Button onClick={onClose}><X /> Close</Button></div>
      <label className="search-field"><Search /><input ref={input} value={query} onChange={event => setQuery(event.target.value)} placeholder="Start typing…" aria-label="Search TorrentFlow" /></label>
      <div className="search-results">{matches.length ? matches.map(match => <button key={match.title} className="search-result" onClick={() => { onGo(match.page); onClose() }}><strong>{match.title}</strong><small>{match.detail}</small></button>) : <div className="empty">No matching releases, feeds or rules.</div>}</div>
      <small className="hint">Esc closes this dialog.</small>
    </section>
  </div>
}

function Dashboard({ addToast, health, releases, loading, error, categories }: { addToast: (message: string) => void; health: ServiceHealth[]; releases: Release[]; loading: boolean; error: string | null; categories: Category[] }) {
  return <>
    <section className="health-grid" aria-label="Service health">
      {loading ? <div className="card loading-card">Loading service health…</div> : health.map(service => <div className="health-chip" key={service.name}><i className={service.status === 'healthy' ? 'status-dot' : 'status-dot warning'} /><div><strong>{service.name} · {service.status === 'healthy' ? 'Healthy' : service.status === 'unconfigured' ? 'Not configured' : 'Degraded'}</strong><small>{service.detail}</small></div></div>)}
    </section>
    <section className="dashboard-grid">
      <article className="card flow-card"><div className="card-heading"><div><span className="eyebrow">24 hour release flow</span><h2>From feed to download</h2></div><Button><ExternalLink /> View events</Button></div><div className="flow"><div><b>48</b><span>discovered</span></div><div><b>9</b><span>matched rules</span></div><div><b>6</b><span>queued to qB</span></div><div><b>1</b><span>needs attention</span></div></div></article>
      <article className="card chart-card"><span className="eyebrow">Live bandwidth · 1 hour</span><div className="metric">42.8 <small>Mb/s</small></div><small className="positive">↑ 12.4 Mb/s</small><div className="chart" aria-label="Download and upload throughput visualisation"><svg viewBox="0 0 600 180" preserveAspectRatio="none" role="img"><path d="M0 135 C60 118 90 150 140 124 S220 54 280 105 S370 155 430 78 S530 42 600 95" fill="none" stroke="#adc6ff" strokeWidth="4"/><path d="M0 154 C65 143 92 160 142 149 S225 132 280 145 S380 167 430 137 S535 165 600 128" fill="none" stroke="#00f4fe" strokeWidth="3" strokeDasharray="9 6"/></svg></div><Button onClick={() => addToast('Live chart paused')}><Gauge /> Pause live updates</Button></article>
      <article className="card recent-card"><div className="card-heading"><div><span className="eyebrow">Recent matches</span><h2>Release decisions</h2></div></div>{error ? <div className="empty"><strong>Could not load current releases</strong><br />{error}</div> : loading ? <div className="empty">Loading release decisions…</div> : releases.length ? <div className="list">{releases.map(release => <ReleaseRow key={release.id} release={release} addToast={addToast} categoryColor={categories.find(category => category.name === release.category)?.color} />)}</div> : <div className="empty">No release decisions yet.</div>}</article>
      <article className="card attention"><span className="eyebrow">Attention queue</span><h2>qBittorrent rejected one request</h2><p>Connection was refused when adding Arcane.S02E01. Retry after qB is online.</p><Button primary onClick={() => addToast('Retry queued')}><RefreshCw /> Retry now</Button></article>
    </section>
  </>
}

function ReleasesPage({ releases, addToast, categories }: { releases: Release[]; addToast: (message: string) => void; categories: Category[] }) {
  const [showAll, setShowAll] = useState(false)
  const visibleCategories = new Set(categories.filter(category => showAll || category.is_interesting).map(category => category.name))
  const filteredReleases = releases.filter(release => visibleCategories.has(release.category))
  return <article className="card releases-card">
    <div className="card-heading"><div><span className="eyebrow">Release queue</span><h2>Latest decisions</h2></div><Button onClick={() => setShowAll(value => !value)}><SlidersHorizontal /> {showAll ? 'Interesting only' : 'All categories'}</Button></div>
    <p className="screen-copy">{showAll ? 'Showing every configured category.' : 'Showing categories marked interesting in Settings.'} Every outcome includes the matching rule and a human-readable reason.</p>
    <div className="data-header" aria-hidden="true"><span>Release</span><span>Source</span><span>Rule</span><span>Scanned</span><span>Outcome</span><span>Action</span></div>
    <div className="list">{filteredReleases.length ? filteredReleases.map(release => <ReleaseRow key={release.id} release={release} addToast={addToast} categoryColor={categories.find(category => category.name === release.category)?.color} />) : <div className="empty"><strong>{releases.length ? 'No releases in the default categories' : 'No releases scanned yet'}</strong><br />{releases.length ? 'Choose All categories or mark a category interesting in Settings.' : 'Run a check on an RSS feed to populate this queue.'}</div>}</div>
  </article>
}

function FeedScanResult({ result }: { result: FeedCheckResult }) {
  return <div className="feed-scan-result" role="status">
    <div className="feed-scan-summary"><strong>Last check: {result.new} new of {result.discovered} releases</strong><span>Showing up to {result.items.length} results</span></div>
    {result.items.length ? <div className="feed-scan-items">{result.items.map(item => <div className="feed-scan-item" key={`${item.title}-${item.status}`}><strong>{item.title}</strong><span>{item.rule_name ? `Rule: ${item.rule_name}` : 'No matching rule'} · {item.status}</span></div>)}</div> : <p>No releases were returned by this feed.</p>}
  </div>
}

function FeedsPage({ feeds, loading, addToast, onCreated, onDeleted }: { feeds: Feed[]; loading: boolean; addToast: (message: string) => void; onCreated: (feed: Feed) => void; onDeleted: (feedId: number) => void }) {
  const [formOpen, setFormOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [scanResults, setScanResults] = useState<Record<number, FeedCheckResult>>({})
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); setSaving(true); setFormError(null); try { const feed = await api.createFeed({ name: String(data.get('name')), url: String(data.get('url')), adapter_type: String(data.get('adapter')), proxy_url: String(data.get('proxy')).trim() || null, interval_minutes: Number(data.get('interval')) }); onCreated(feed); setFormOpen(false); addToast('RSS feed added') } catch { setFormError('Could not save feed. Check the URL and API connection.') } finally { setSaving(false) } }
  const check = async (feed: Feed) => { try { const result = await api.checkFeed(feed.id); setScanResults(current => ({ ...current, [feed.id]: result })); addToast(`${feed.name}: ${result.new} new of ${result.discovered} found`) } catch { addToast(`${feed.name}: check failed`) } }
  const remove = async (feed: Feed) => { if (!window.confirm(`Delete “${feed.name}” and its stored releases?`)) return; try { await api.deleteFeed(feed.id); setScanResults(current => { const { [feed.id]: _, ...rest } = current; return rest }); onDeleted(feed.id); addToast(`${feed.name} deleted`) } catch { addToast(`${feed.name}: could not delete feed`) } }
  return <article className="card releases-card"><div className="card-heading"><div><span className="eyebrow">Source monitoring</span><h2>RSS feeds</h2></div><Button primary onClick={() => setFormOpen(true)}><Plus /> Add feed</Button></div><p className="screen-copy">Sources stay enabled through transient errors. Review health, schedule and next permitted check.</p>{formOpen && <form className="feed-form" onSubmit={submit}><label>Name<input name="name" required placeholder="e.g. TorrentLeech" /></label><label>RSS URL<input name="url" type="url" required placeholder="https://…" /></label><label>Adapter<select name="adapter"><option value="generic_rss">Generic RSS</option><option value="torrentleech">TorrentLeech</option></select></label><label>Proxy (optional)<input name="proxy" placeholder="socks5://127.0.0.1:1080" /></label><label>Interval<select name="interval" defaultValue="30"><option value="10">10 minutes</option><option value="30">30 minutes</option><option value="60">60 minutes</option></select></label><div className="form-actions"><Button onClick={() => setFormOpen(false)}>Cancel</Button><Button primary>{saving ? 'Saving…' : 'Save feed'}</Button></div>{formError && <p className="form-error">{formError}</p>}</form>}{loading ? <div className="empty">Loading RSS feeds…</div> : feeds.length ? <div className="list">{feeds.map(feed => <div key={feed.id}><div className="data-row"><div className="release-name"><strong>{feed.name}</strong><small>{feed.adapter_type.replace('_', ' ')} · {feed.url}{feed.proxy_url ? ' · proxy' : ''}</small></div><span>{feed.interval_minutes} min</span><span>Enabled</span><span>—</span><Badge warning={!feed.enabled}>{feed.enabled ? 'Healthy' : 'Paused'}</Badge><div className="feed-actions"><Button onClick={() => check(feed)}><RefreshCw /> Check now</Button><Button label={`Delete ${feed.name}`} onClick={() => remove(feed)}><Trash2 /> Delete</Button></div></div>{scanResults[feed.id] && <FeedScanResult result={scanResults[feed.id]} />}</div>)}</div> : <div className="empty"><strong>No RSS feeds yet</strong><br />Add a source to start evaluating releases.</div>}</article>
}

function LoginScreen({ onLoggedIn }: { onLoggedIn: () => void }) { const [error, setError] = useState<string | null>(null); const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); try { await api.login(String(new FormData(event.currentTarget).get('password'))); onLoggedIn() } catch { setError('Incorrect password.') } }; return <main className="login"><form className="login-card" onSubmit={submit}><Waves /><span className="eyebrow">TorrentFlow · LAN control room</span><h1>Sign in</h1><p>Enter the administrator password configured for this TorrentFlow instance.</p><label>Password<input name="password" type="password" autoFocus required /></label>{error && <p className="form-error">{error}</p>}<Button primary submit>Sign in</Button></form></main> }

function RulesPage({ rules, onCreated, addToast, categories }: { rules: Rule[]; onCreated: (rule: Rule) => void; addToast: (message: string) => void; categories: Category[] }) {
  const [open, setOpen] = useState(false)
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const maxSizeGb = Number(data.get('maxSizeGb'))
    const rule = await api.createRule({ name: String(data.get('name')), include_keywords: String(data.get('keywords')), min_seeds: Number(data.get('seeds')), action: String(data.get('action')) as Rule['action'], priority: Number(data.get('priority')), category: String(data.get('category')), freeleech_only: data.get('freeleech') === 'on', double_upload_only: data.get('doubleUpload') === 'on', max_size_bytes: Number.isFinite(maxSizeGb) && maxSizeGb > 0 ? Math.round(maxSizeGb * 1024 ** 3) : null, uploader_whitelist: String(data.get('uploaderWhitelist')).trim(), uploader_blacklist: String(data.get('uploaderBlacklist')).trim(), qb_category: String(data.get('qbCategory')).trim(), save_path: String(data.get('savePath')).trim() })
    onCreated(rule); setOpen(false); addToast('Rule created')
  }
  const actionLabel = (action: Rule['action']) => action === 'auto_add' ? 'Auto-add' : action === 'both' ? 'Notify + auto-add' : 'Notify'
  return <article className="card releases-card"><div className="card-heading"><div><span className="eyebrow">Automation policy</span><h2>Prioritised rules</h2></div><Button primary onClick={() => setOpen(true)}><Plus /> Create rule</Button></div><p className="screen-copy">Rules evaluate all filled conditions together; comma-separated keywords match any item.</p>{open && <form className="feed-form rule-form" onSubmit={submit}><label>Name<input name="name" required /></label><label>Keywords<input name="keywords" placeholder="ubuntu,debian" /></label><label>Min seeds<input name="seeds" type="number" min="0" defaultValue="0" /></label><label>Category<select name="category" defaultValue={categories[0]?.name} required>{categories.map(category => <option key={category.id} value={category.name}>{category.name}</option>)}</select></label><label>Action<select name="action"><option value="notify">Notify</option><option value="auto_add">Auto-add</option><option value="both">Notify + auto-add</option></select></label><label>Priority<input name="priority" type="number" min="0" defaultValue="100" /></label><details className="rule-conditions"><summary>Automation gates and qBittorrent target</summary><label><input name="freeleech" type="checkbox" /> Freeleech only</label><label><input name="doubleUpload" type="checkbox" /> Double upload only</label><label>Max size (GiB)<input name="maxSizeGb" type="number" min="0" step="0.1" placeholder="No limit" /></label><label>Uploader allow-list<input name="uploaderWhitelist" placeholder="trusted-uploader,another" /></label><label>Uploader block-list<input name="uploaderBlacklist" placeholder="blocked-uploader" /></label><label>qBittorrent category<input name="qbCategory" placeholder="movies" /></label><label>qBittorrent save path<input name="savePath" placeholder="/downloads/movies" /></label></details><div className="form-actions"><Button onClick={() => setOpen(false)}>Cancel</Button><Button primary>Save rule</Button></div></form>}<div className="list">{rules.length ? rules.map(rule => <div className="data-row" key={rule.id}><div className="release-name"><strong><i className={`release-marker ${rule.category}`} style={{ backgroundColor: categories.find(category => category.name === rule.category)?.color }} aria-hidden="true" />{String(rule.priority).padStart(2, '0')} · {rule.name}</strong><small>{rule.include_keywords || 'No keywords'} · min {rule.min_seeds} seeds{rule.freeleech_only ? ' · freeleech' : ''}{rule.qb_category ? ` · qB: ${rule.qb_category}` : ''}</small></div><span className={`category-label ${rule.category}`} style={{ color: categories.find(category => category.name === rule.category)?.color }}>{rule.category}</span><span>{actionLabel(rule.action)}</span><span>—</span><Badge>Active</Badge><Button>Edit</Button></div>) : <div className="empty">No rules yet. Create a rule to evaluate incoming releases.</div>}</div></article>
}

function formatSpeed(bytes: number) { return bytes <= 0 ? '—' : `${(bytes / 1_000_000).toFixed(1)} MB/s` }
function formatTime(value: string) { return new Date(value).toLocaleString() }
function isNotification(event: AuditEvent) { return event.event_type.startsWith('telegram.') }

function DownloadsPage({ addToast }: { addToast: (message: string) => void }) {
  const [downloads, setDownloads] = useState<DownloadItem[] | null>(null); const [error, setError] = useState<string | null>(null)
  const load = async () => { setError(null); try { setDownloads(await api.downloads()) } catch { setError('qBittorrent did not return its download list. Check the connection in Settings.') } }
  useEffect(() => { void load() }, [])
  return <article className="card releases-card"><div className="card-heading"><div><span className="eyebrow">qBittorrent</span><h2>Active downloads</h2></div><Button onClick={() => void load()}><RefreshCw /> Refresh</Button></div><p className="screen-copy">Read-only progress from qBittorrent. Use qBittorrent itself for torrent controls.</p>{error ? <div className="empty"><strong>Could not load downloads</strong><br />{error}</div> : downloads === null ? <div className="empty">Loading qBittorrent downloads…</div> : downloads.length ? <div className="list">{downloads.map(download => <div className="data-row" key={download.name}><div className="release-name"><strong>{download.name}</strong><small>{download.state} · {formatSpeed(download.dlspeed)}</small></div><span>{Math.round(download.progress * 100)}%</span><span className="download-progress"><i style={{ width: `${Math.round(download.progress * 100)}%` }} /></span><Badge>{download.state}</Badge><Button onClick={() => addToast(`${download.name}: ${Math.round(download.progress * 100)}% complete`)}><Check /> Inspect</Button></div>)}</div> : <div className="empty"><strong>No active downloads</strong><br />qBittorrent will appear here with speed and progress as soon as it reports a torrent.</div>}</article>
}

function AuditList({ events, empty }: { events: AuditEvent[]; empty: string }) { return events.length ? <div className="list">{events.map(event => <div className="data-row" key={event.id}><div className="release-name"><strong>{event.message}</strong><small>{formatTime(event.created_at)}</small></div><span className="category-label">{event.event_type.split('.')[0]}</span><span>{event.event_type}</span><span>{formatTime(event.created_at)}</span><Badge warning={event.event_type.endsWith('failed')}>{event.event_type.endsWith('failed') ? 'Failed' : 'Recorded'}</Badge><span /></div>)}</div> : <div className="empty">{empty}</div> }

function HistoryPage() {
  const [events, setEvents] = useState<AuditEvent[] | null>(null); const [error, setError] = useState<string | null>(null)
  useEffect(() => { api.audit().then(setEvents).catch(() => setError('The audit history could not be loaded. Check the API connection.')) }, [])
  return <article className="card releases-card"><div className="card-heading"><div><span className="eyebrow">Audit trail</span><h2>History</h2></div></div><p className="screen-copy">Recorded release, delivery, and integration events. The newest 200 events are shown.</p>{error ? <div className="empty"><strong>Could not load history</strong><br />{error}</div> : events === null ? <div className="empty">Loading audit history…</div> : <AuditList events={events} empty="No audit events have been recorded yet." />}</article>
}

function NotificationsPage({ addToast }: { addToast: (message: string) => void }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null); const [error, setError] = useState<string | null>(null); const [testing, setTesting] = useState(false)
  useEffect(() => { api.audit().then(events => setEvents(events.filter(isNotification))).catch(() => setError('The notification log could not be loaded. Check the API connection.')) }, [])
  const test = async () => { setTesting(true); try { await api.testTelegram(); addToast('Telegram test message sent'); setEvents(current => current ? [{ id: Date.now(), event_type: 'telegram.tested', message: 'Telegram test message sent', created_at: new Date().toISOString() }, ...current] : current) } catch { addToast('Telegram test failed. Check Settings.') } finally { setTesting(false) } }
  return <article className="card releases-card"><div className="card-heading"><div><span className="eyebrow">Telegram</span><h2>Delivery log</h2></div><Button primary onClick={() => void test()}>{testing ? 'Testing…' : <><Bell /> Test Telegram</>}</Button></div><p className="screen-copy">Only Telegram delivery attempts appear here. Configuration stays in environment variables.</p>{error ? <div className="empty"><strong>Could not load notification log</strong><br />{error}</div> : events === null ? <div className="empty">Loading notification log…</div> : <AuditList events={events} empty="No Telegram messages have been attempted yet." />}</article>
}

function SettingsPage({ addToast, categories, onCategoryCreated, onCategoryUpdated }: { addToast: (message: string) => void; categories: Category[]; onCategoryCreated: (category: Category) => void; onCategoryUpdated: (category: Category) => void }) {
  const [status, setStatus] = useState<IntegrationStatus | null>(null); const [error, setError] = useState<string | null>(null); const [testing, setTesting] = useState<'qbit' | 'telegram' | null>(null)
  const [categoryError, setCategoryError] = useState<string | null>(null)
  const [disk, setDisk] = useState<DiskStatus | null>(null)
  const load = async () => { setError(null); try { setStatus(await api.integrationStatus()) } catch { setError('Integration status could not be loaded. Check the API connection.') } }
  useEffect(() => { void load(); api.disk().then(setDisk).catch(() => setDisk(null)) }, [])
  const test = async (kind: 'qbit' | 'telegram') => { setTesting(kind); try { kind === 'qbit' ? await api.testQbit() : await api.testTelegram(); addToast(`${kind === 'qbit' ? 'qBittorrent' : 'Telegram'} connection test succeeded`) } catch { addToast(`${kind === 'qbit' ? 'qBittorrent' : 'Telegram'} connection test failed`) } finally { setTesting(null) } }
  const createCategory = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); setCategoryError(null); try { const category = await api.createCategory({ name: String(data.get('name')).trim().toLowerCase(), color: String(data.get('color')), is_interesting: true }); onCategoryCreated(category); event.currentTarget.reset(); addToast(`${category.name} category added`) } catch { setCategoryError('Use a unique lowercase name with letters, numbers, hyphens or underscores.') } }
  const toggleCategory = async (category: Category) => { try { onCategoryUpdated(await api.updateCategory(category.id, { is_interesting: !category.is_interesting })) } catch { addToast(`Could not update ${category.name}`) } }
  const configured = (value: boolean | undefined) => value ? <Badge>Configured</Badge> : <Badge warning>Not configured</Badge>
  const exportConfig = async () => { try { const configJson = await api.exportConfiguration(); const url = URL.createObjectURL(new Blob([configJson], { type: 'application/json' })); const link = document.createElement('a'); link.href = url; link.download = 'torrentflow-config.json'; link.click(); URL.revokeObjectURL(url); addToast('Configuration exported without secrets') } catch { addToast('Configuration export failed') } }
  const importConfig = async (event: FormEvent<HTMLInputElement>) => { const file = event.currentTarget.files?.[0]; if (!file) return; try { const result = await api.importConfiguration(await file.text()); addToast(`Configuration merged: ${result.feeds} feeds, ${result.rules} rules`); event.currentTarget.value = '' } catch { addToast('Configuration import failed. Use a valid TorrentFlow JSON or YAML file.') } }
  return <article className="card page-card"><div className="card-heading"><div><span className="eyebrow">Integrations</span><h2>Connections and categories</h2></div><Button onClick={() => void load()}><RefreshCw /> Refresh</Button></div><p>Credentials are read only from environment variables and are never shown here or stored in SQLite.</p>{error ? <div className="empty"><strong>Could not load integration status</strong><br />{error}</div> : status === null ? <div className="empty">Loading integration status…</div> : <div className="settings-grid"><div className="settings-status"><strong>qBittorrent</strong><small>Feeds the read-only Downloads screen and accepts auto-add rules when configured.</small>{configured(status.qbit_configured)}<Button primary onClick={() => void test('qbit')}>{testing === 'qbit' ? 'Testing…' : 'Test connection'}</Button></div><div className="settings-status"><strong>Telegram</strong><small>Sends release notifications and records each delivery attempt in the audit log.</small>{configured(status.telegram_configured)}<Button primary onClick={() => void test('telegram')}>{testing === 'telegram' ? 'Testing…' : 'Send test message'}</Button></div><div className="settings-status"><strong>Disk space</strong><small>{disk ? disk.detail : 'Disk monitor is unavailable.'}</small>{disk ? <Badge warning={disk.state !== 'healthy'}>{disk.free_percent === null ? disk.state : `${disk.free_percent}% free`}</Badge> : <Badge warning>Unknown</Badge>}</div></div>}<section className="category-settings"><div><span className="eyebrow">Configuration backup</span><h2>Export or import</h2><p className="screen-copy">Configuration files contain feeds, rules and categories, but never passwords or integration keys.</p><div className="form-actions"><Button onClick={() => void exportConfig()}>Export JSON</Button><label><span className="sr-only">Import configuration</span><input type="file" accept=".json,.yaml,.yml,application/json,application/yaml" onChange={event => void importConfig(event)} /></label></div></div><div><span className="eyebrow">Release categories</span><h2>Default release filter</h2><p className="screen-copy">Marked categories appear when Releases opens. Use All categories there to inspect everything else.</p></div><div className="category-list">{categories.map(category => <label className="category-control" key={category.id}><input type="checkbox" checked={category.is_interesting} onChange={() => void toggleCategory(category)} /><i style={{ backgroundColor: category.color }} /><span>{category.name}</span><small>{category.is_interesting ? 'Shown by default' : 'Hidden by default'}</small></label>)}</div><form className="category-form" onSubmit={createCategory}><label>Name<input name="name" required pattern="[a-z0-9][a-z0-9_-]*" placeholder="movies" /></label><label>Color<input name="color" type="color" defaultValue="#ad8cff" /></label><Button primary submit><Plus /> Add category</Button>{categoryError && <p className="form-error">{categoryError}</p>}</form></section></article>
}

export function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [searchOpen, setSearchOpen] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [health, setHealth] = useState<ServiceHealth[]>([])
  const [apiReleases, setApiReleases] = useState<Release[]>(fallbackReleases)
  const [feeds, setFeeds] = useState<Feed[]>([])
  const [rules, setRules] = useState<Rule[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  useEffect(() => {
    api.me().then(session => setAuthenticated(session.authenticated)).catch(() => setAuthenticated(false))
  }, [])
  useEffect(() => {
    if (!authenticated) return
    const controller = new AbortController()
    Promise.all([api.health(controller.signal), api.releases(controller.signal), api.feeds(controller.signal), api.rules(controller.signal), api.categories()])
      .then(([healthResponse, releaseResponse, feedResponse, ruleResponse, categoryResponse]) => { setHealth(healthResponse.services); setApiReleases(releaseResponse); setFeeds(feedResponse); setRules(ruleResponse); setCategories(categoryResponse); setApiError(null) })
      .catch(error => { if (error.name !== 'AbortError') setApiError('Check that the TorrentFlow API is running.') })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [authenticated])
  const addToast = (message: string) => { const toast = { id: Date.now(), message }; setToasts(current => [...current, toast]); window.setTimeout(() => setToasts(current => current.filter(item => item.id !== toast.id)), 2600) }
  const current = pages.find(item => item.id === page)!
  if (authenticated === null) return <main className="login"><div className="login-card">Checking secure session…</div></main>
  if (!authenticated) return <LoginScreen onLoggedIn={() => setAuthenticated(true)} />
  return <div className="app-shell"><aside className="rail"><div className="brand" aria-label="TorrentFlow"><Waves /></div><nav aria-label="Primary navigation">{pages.map(({ id, label, icon: Icon }) => <button key={id} className={page === id ? 'active' : ''} type="button" title={label} aria-label={label} aria-current={page === id ? 'page' : undefined} onClick={() => setPage(id)}><Icon /></button>)}</nav></aside>
    <main className="main"><header className="topbar"><div><span className="eyebrow">TorrentFlow · NAS control room</span><h1>{current.label}</h1></div><div className="top-actions"><Button onClick={() => setSearchOpen(true)}><Search /> Search</Button><Button primary onClick={() => addToast('Feed check queued')}><RefreshCw /> Check feeds</Button></div></header>{page === 'dashboard' ? <Dashboard addToast={addToast} health={health} releases={apiReleases} loading={loading} error={apiError} categories={categories} /> : page === 'feeds' ? <FeedsPage feeds={feeds} loading={loading} addToast={addToast} onCreated={feed => setFeeds(currentFeeds => [...currentFeeds, feed])} onDeleted={feedId => setFeeds(currentFeeds => currentFeeds.filter(feed => feed.id !== feedId))} /> : page === 'rules' ? <RulesPage rules={rules} onCreated={rule => setRules(currentRules => [...currentRules, rule].sort((a, b) => a.priority - b.priority))} addToast={addToast} categories={categories} /> : page === 'releases' ? <ReleasesPage releases={apiReleases} addToast={addToast} categories={categories} /> : page === 'downloads' ? <DownloadsPage addToast={addToast} /> : page === 'history' ? <HistoryPage /> : page === 'notifications' ? <NotificationsPage addToast={addToast} /> : <SettingsPage addToast={addToast} categories={categories} onCategoryCreated={category => setCategories(current => [...current, category].sort((a, b) => a.name.localeCompare(b.name)))} onCategoryUpdated={category => setCategories(current => current.map(item => item.id === category.id ? category : item))} />}</main>
    <nav className="mobile-nav" aria-label="Mobile navigation">{pages.map(({ id, label, icon: Icon }) => <button key={id} type="button" className={page === id ? 'active' : ''} aria-current={page === id ? 'page' : undefined} onClick={() => setPage(id)}><Icon /><span>{label}</span></button>)}</nav>
    <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} onGo={setPage} releases={apiReleases} />
    <div className="toast-stack" aria-live="polite">{toasts.map(toast => <div className="toast" key={toast.id}>{toast.message}</div>)}</div>
  </div>
}
