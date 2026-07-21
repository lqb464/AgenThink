/** Client-side JWT storage + helpers. */

const ACCESS_KEY = "agenthink_access_token";
const REFRESH_KEY = "agenthink_refresh_token";
const USER_KEY = "agenthink_user";
const LANG_KEY = "agenthink_language";
const MODEL_KEY = "agenthink_model_profile";

export type AuthUser = {
  id: string;
  email: string;
  rag_project_id: string;
};

export type ModelProfile = "gemini" | "openai" | "local";

export type UiPrefs = {
  language: "vi" | "en";
  modelProfile: ModelProfile;
  localPreset?: "ollama" | "vllm";
  localModel?: string;
};

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function setAuthSession(
  access: string,
  refresh: string,
  user: AuthUser
): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthSession(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

export function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    ...(extra as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export function getUiPrefs(): UiPrefs {
  if (typeof window === "undefined") {
    return { language: "vi", modelProfile: "gemini" };
  }
  const language = (localStorage.getItem(LANG_KEY) as "vi" | "en") || "vi";
  let modelProfile: ModelProfile = "gemini";
  let localPreset: "ollama" | "vllm" | undefined;
  let localModel: string | undefined;
  try {
    const raw = localStorage.getItem(MODEL_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.modelProfile) modelProfile = parsed.modelProfile;
      localPreset = parsed?.localPreset;
      localModel = parsed?.localModel;
    }
  } catch {
    /* ignore */
  }
  return { language, modelProfile, localPreset, localModel };
}

export function setLanguage(lang: "vi" | "en"): void {
  localStorage.setItem(LANG_KEY, lang);
}

export function setModelProfile(prefs: Partial<UiPrefs> & { modelProfile: ModelProfile }): void {
  const cur = getUiPrefs();
  localStorage.setItem(
    MODEL_KEY,
    JSON.stringify({
      modelProfile: prefs.modelProfile,
      localPreset: prefs.localPreset ?? cur.localPreset,
      localModel: prefs.localModel ?? cur.localModel,
    })
  );
}
