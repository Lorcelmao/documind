// fallback matches the api port mapping in docker-compose.yml
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

// Access token lives in memory only; the refresh token is an httpOnly cookie
// managed by the API, so a page reload recovers the session via /auth/refresh.
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(`${API_URL}${path}`, { ...init, headers, credentials: "include" });
}

let refreshInFlight: Promise<boolean> | null = null;

// Single-flight: concurrent callers share one request, so our own code never
// replays a rotated refresh cookie (two tabs, re-run effects, parallel 401s).
export function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function doRefresh(): Promise<boolean> {
  const res = await request("/auth/refresh", { method: "POST" });
  if (!res.ok) return false;
  const data = await res.json();
  accessToken = data.access_token;
  return true;
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  let res = await request(path, init);
  if (res.status === 401 && (await refreshSession())) {
    res = await request(path, init);
  }
  return res;
}
