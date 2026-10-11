// Small HTTP adapter. The UI never computes decisions; it only reads and writes API JSON.

const BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "/api";

export class APIError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "APIError";
    this.status = status;
  }
}

export function customerPath(customerId: string, suffix = ""): string {
  return `/customers/${encodeURIComponent(customerId)}${suffix}`;
}

function query(params?: Record<string, string | number | undefined | null>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!entries.length) return "";
  return "?" + new URLSearchParams(entries.map(([key, value]) => [key, String(value)])).toString();
}

async function request<T>(method: "GET" | "POST", path: string, init: { params?: Record<string, any>; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE + path + query(init.params), {
      method,
      headers: init.body === undefined ? undefined : { "content-type": "application/json" },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      signal: init.signal,
    });
  } catch (error) {
    if ((error as Error)?.name === "AbortError") throw error;
    throw new APIError("Can't reach the Greenr API. Start it with make api (or make app), then refresh.");
  }
  if (!response.ok) {
    const code = response.status;
    let message =
      code === 404 ? "Customer or product not found." :
      code === 502 || code === 503 || code === 504 ? "Can't reach the Greenr API. Start it with make api (or make app), then refresh." :
      "The API couldn't complete this request.";
    if (code === 409 || code === 422 || code === 403) {
      try {
        const detail = (await response.json())?.detail;
        if (typeof detail === "string") message = detail.slice(0, 500);
        else if (Array.isArray(detail) && detail[0]?.msg) message = String(detail[0].msg).slice(0, 500);
      } catch {
        // Keep the generic message when the error body isn't JSON.
      }
    }
    throw new APIError(`${message} (HTTP ${code})`, code);
  }
  let result: unknown;
  try {
    result = await response.json();
  } catch {
    throw new APIError("The API returned a response that isn't valid JSON.");
  }
  if (typeof result !== "object" || result === null) {
    throw new APIError("The API response doesn't match the expected shape.");
  }
  return result as T;
}

export const api = {
  get: <T>(path: string, params?: Record<string, any>, signal?: AbortSignal) => request<T>("GET", path, { params, signal }),
  post: <T>(path: string, body: unknown, signal?: AbortSignal) => request<T>("POST", path, { body, signal }),
};

export function requestId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
