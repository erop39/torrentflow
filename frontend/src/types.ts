export type Page = 'dashboard' | 'feeds' | 'releases' | 'rules' | 'downloads' | 'history' | 'notifications' | 'settings'
export type Health = 'healthy' | 'degraded'

export type ServiceHealth = { name: string; status: Health; detail: string }
export type HealthResponse = { services: ServiceHealth[]; checked_at: string }
export type Feed = { id: number; name: string; url: string; adapter_type: string; enabled: boolean; interval_minutes: number }
export type FeedCheckResult = { discovered: number; new: number; items: Array<{ title: string; status: string; rule_name: string | null; category: string; seeds: number }> }
export type IntegrationStatus = { qbit_configured: boolean; telegram_configured: boolean }
export type Category = { id: number; name: string; color: string; is_interesting: boolean }
export type DownloadItem = { name: string; progress: number; state: string; dlspeed: number }
export type AuditEvent = { id: number; event_type: string; message: string; created_at: string }
export type Rule = { id: number; name: string; include_keywords: string; min_seeds: number; action: 'notify' | 'auto_add' | 'both'; priority: number; category: string; enabled: boolean }

export type Release = {
  id: number
  title: string
  link: string
  source: string
  rule_name: string | null
  status: string
  category: string
  seeds: number
  created_at: string
}

export type Toast = { id: number; message: string }
