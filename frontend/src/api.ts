const TOKEN_KEY = "pulsegrid_token";

export type JobStatus =
  | "PENDING"
  | "RUNNING"
  | "PAUSED"
  | "STOPPED"
  | "COMPLETED";

export type Platform = "bookmyshow" | "district" | "mock";

export interface TrackingJob {
  id: number;
  user_id: number;
  target_name: string;
  platform: string;
  city: string;
  theater: string;
  target_date: string;
  start_at: string;
  end_at: string;
  poll_interval_seconds: number;
  status: JobStatus | string;
  created_at: string;
  updated_at: string;
  last_checked_at: string | null;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(path, { ...options, headers });

  if (response.status === 401) {
    clearToken();
    throw new Error("Unauthorized — please sign in again.");
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map((d: { msg?: string }) => d.msg ?? d).join("; ");
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function login(telegramUserId: number): Promise<string> {
  const data = await request<{ access_token: string }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ telegram_user_id: telegramUserId }),
  });
  setToken(data.access_token);
  return data.access_token;
}

export async function listJobs(): Promise<TrackingJob[]> {
  return request<TrackingJob[]>("/api/v1/jobs");
}

export async function pauseJob(id: number): Promise<TrackingJob> {
  return request<TrackingJob>(`/api/v1/jobs/${id}/pause`, { method: "POST" });
}

export async function resumeJob(id: number): Promise<TrackingJob> {
  return request<TrackingJob>(`/api/v1/jobs/${id}/resume`, { method: "POST" });
}

export async function startJob(id: number): Promise<TrackingJob> {
  return request<TrackingJob>(`/api/v1/jobs/${id}/start`, { method: "POST" });
}

export async function stopJob(id: number): Promise<TrackingJob> {
  return request<TrackingJob>(`/api/v1/jobs/${id}/stop`, { method: "POST" });
}

export async function deleteJob(id: number): Promise<void> {
  await request<{ message: string; id: number }>(`/api/v1/jobs/${id}`, {
    method: "DELETE",
  });
}
