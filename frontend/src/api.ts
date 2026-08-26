import type {
  AuditEvent,
  Category,
  DiskStatus,
  DiskThreshold,
  DownloadItem,
  Feed,
  FeedCheckResult,
  HealthResponse,
  IntegrationStatus,
  Release,
  Rule,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    signal,
    credentials: "include",
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

async function sendJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

async function deleteJson(path: string): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

async function putJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

async function getText(path: string): Promise<string> {
  const response = await fetch(`${API_URL}${path}`, { credentials: "include" });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.text();
}

async function sendText<T>(
  path: string,
  body: string,
  contentType: string,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": contentType },
    body,
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  health: (signal?: AbortSignal) =>
    getJson<HealthResponse>("/api/health", signal),
  releases: (signal?: AbortSignal) =>
    getJson<Release[]>("/api/releases", signal),
  feeds: (signal?: AbortSignal) => getJson<Feed[]>("/api/feeds", signal),
  me: (signal?: AbortSignal) =>
    getJson<{ authenticated: boolean }>("/api/auth/me", signal),
  login: (password: string) =>
    sendJson<{ authenticated: boolean }>("/api/auth/login", { password }),
  createFeed: (
    payload: Pick<
      Feed,
      "name" | "url" | "adapter_type" | "proxy_url" | "interval_minutes"
    >,
  ) => sendJson<Feed>("/api/feeds", payload),
  deleteFeed: (feedId: number) => deleteJson(`/api/feeds/${feedId}`),
  rules: (signal?: AbortSignal) => getJson<Rule[]>("/api/rules", signal),
  createRule: (payload: Omit<Rule, "id" | "enabled">) =>
    sendJson<Rule>("/api/rules", payload),
  categories: () => getJson<Category[]>("/api/categories"),
  createCategory: (
    payload: Pick<Category, "name" | "color" | "is_interesting">,
  ) => sendJson<Category>("/api/categories", payload),
  updateCategory: (
    categoryId: number,
    payload: Partial<Pick<Category, "color" | "is_interesting">>,
  ) => patchJson<Category>(`/api/categories/${categoryId}`, payload),
  checkFeed: (feedId: number) =>
    sendJson<FeedCheckResult>(`/api/feeds/${feedId}/check`),
  downloads: () => getJson<DownloadItem[]>("/api/downloads"),
  audit: () => getJson<AuditEvent[]>("/api/audit"),
  integrationStatus: () =>
    getJson<IntegrationStatus>("/api/integrations/status"),
  testQbit: () =>
    sendJson<{ ok: boolean }>("/api/integrations/qbittorrent/test"),
  testTelegram: () =>
    sendJson<{ ok: boolean }>("/api/integrations/telegram/test"),
  disk: () => getJson<DiskStatus>("/api/system/disk"),
  diskThreshold: () => getJson<DiskThreshold>("/api/settings/disk"),
  updateDiskThreshold: (disk_free_threshold_percent: number) =>
    putJson<DiskThreshold>("/api/settings/disk", {
      disk_free_threshold_percent,
    }),
  saveTrackerCredentials: (
    feedId: number,
    payload: { cookie?: string; passkey?: string },
  ) =>
    putJson<{ configured: boolean }>(
      `/api/feeds/${feedId}/credentials`,
      payload,
    ),
  exportConfiguration: (format: "json" | "yaml" = "json") =>
    getText(`/api/config/export?format=${format}`),
  importConfiguration: (document: string) =>
    sendText<{
      mode: string;
      feeds: number;
      rules: number;
      categories: number;
    }>("/api/config/import", document, "application/yaml"),
};
