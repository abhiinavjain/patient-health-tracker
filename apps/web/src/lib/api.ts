// Browser-side API client. All calls go through the Next.js proxy (/api/proxy/*), which adds the auth token.

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d))
      return d
        .map((e) => (e && typeof e === "object" && "msg" in e ? String((e as { msg: unknown }).msg) : String(e)))
        .join("; ");
  }
  return fallback;
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`/api/proxy${path}`, {
    method: init.method ?? "GET",
    headers: init.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });
  if (res.status === 401) {
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      // Deliberate full reload on session expiry: clears all client state and runs the route guard.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    }
    throw new ApiError(401, "Your session has expired. Please sign in again.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, detailMessage(body, `Request failed (${res.status})`));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function authRequest<T>(path: "login" | "signup" | "logout", body?: unknown): Promise<T> {
  const res = await fetch(`/api/auth/${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, detailMessage(data, "Something went wrong"));
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}
