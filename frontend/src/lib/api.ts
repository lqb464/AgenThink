import {
  DocsStatusResponse,
  HealthResponse,
  Message,
  SessionSummary,
} from "./types";
import { authHeaders, clearAuthSession, getRefreshToken, setAuthSession } from "./auth";

const API_BASE = "/api";

async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setAuthSession(data.access_token, data.refresh_token, data.user);
    return true;
  } catch {
    return false;
  }
}

/** Fetch with Bearer JWT; on 401 try refresh once. */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
  retry = true
): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const auth = authHeaders();
  Object.entries(auth as Record<string, string>).forEach(([k, v]) => {
    if (!headers.has(k)) headers.set(k, v);
  });
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) return apiFetch(path, init, false);
    clearAuthSession();
  }
  return res;
}

export async function registerUser(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail.slice(0, 200) || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function loginUser(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail.slice(0, 200) || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchMe() {
  const res = await apiFetch("/auth/me");
  if (!res.ok) return null;
  return res.json();
}

export async function fetchSessions(): Promise<SessionSummary[]> {
  try {
    const res = await apiFetch("/sessions", { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.sessions || [];
  } catch (error) {
    console.error("Failed to fetch sessions:", error);
    return [];
  }
}

export async function fetchSessionMessages(sessionId: string): Promise<Message[]> {
  try {
    const res = await apiFetch(`/sessions/${sessionId}`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    const messages = (data.messages || []) as Message[];
    return messages.map((m, idx) => ({
      ...m,
      id: m.id || `${m.role}-${idx}`,
    }));
  } catch (error) {
    console.error(`Failed to fetch messages for session ${sessionId}:`, error);
    return [];
  }
}

export async function deleteSession(sessionId: string): Promise<boolean> {
  try {
    const res = await apiFetch(`/sessions/${sessionId}`, { method: "DELETE" });
    return res.ok;
  } catch (error) {
    console.error(`Failed to delete session ${sessionId}:`, error);
    return false;
  }
}

export async function fetchHealth(): Promise<HealthResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error("Failed to fetch health check:", error);
    return null;
  }
}

const PROJECT_KEY = "agenthink_rag_project_id";
const FILTER_KEY = "agenthink_rag_source_filter";

export function getStoredProjectId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(PROJECT_KEY) || "";
}

export function setStoredProjectId(id: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(PROJECT_KEY, id.trim());
}

export function getStoredSourceFilter(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(FILTER_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function setStoredSourceFilter(files: string[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(FILTER_KEY, JSON.stringify(files));
}

export async function fetchDocsStatus(projectId?: string): Promise<DocsStatusResponse | null> {
  try {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
    const res = await apiFetch(`/docs/status${q}`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error("Failed to fetch docs status:", error);
    return null;
  }
}

export async function ensureDocsProject(
  projectId: string,
  name?: string
): Promise<DocsStatusResponse["project"] | null> {
  try {
    const res = await apiFetch(`/docs/project`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId, name: name || undefined }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error("Failed to ensure docs project:", error);
    return null;
  }
}

export async function uploadDocs(
  files: File[],
  projectId?: string
): Promise<{ ok?: boolean; added?: string[]; sources?: string[]; error?: string } | null> {
  try {
    const form = new FormData();
    if (projectId) form.append("project_id", projectId);
    files.forEach((f) => form.append("files", f));
    const res = await apiFetch(`/docs/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const detail = await res.text();
      return { error: detail.slice(0, 200) || `HTTP ${res.status}` };
    }
    return await res.json();
  } catch (error) {
    console.error("Upload failed:", error);
    return { error: "Không kết nối được API Tri thức" };
  }
}

export async function deleteDocSource(
  filename: string,
  projectId?: string
): Promise<{ ok?: boolean; sources?: string[]; error?: string } | null> {
  try {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
    const res = await apiFetch(`/docs/sources/${encodeURIComponent(filename)}${q}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      return { error: `HTTP ${res.status}` };
    }
    return await res.json();
  } catch (error) {
    console.error("Delete source failed:", error);
    return { error: "Không kết nối được API Tri thức" };
  }
}
