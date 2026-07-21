/**
 * Resolve the FastAPI base URL.
 *
 * Empty-string env must not win over the fallback — otherwise
 * `fetch("" + "/api/v1/...")` hits the Next.js origin and 404s.
 */
function trimEnv(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

export function getApiBase(): string {
  const publicUrl = trimEnv(process.env.NEXT_PUBLIC_API_URL);
  if (typeof window === "undefined") {
    return (
      trimEnv(process.env.API_INTERNAL_URL) ??
      publicUrl ??
      "http://localhost:8000"
    );
  }
  return publicUrl ?? "http://localhost:8000";
}

type ApiOptions = RequestInit & {
  token?: string;
};

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** Turn FastAPI `detail` (string or validation array) into a user-facing message. */
export function formatApiDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const msg = String((item as { msg: unknown }).msg);
          const loc = (item as { loc?: unknown[] }).loc;
          const field =
            Array.isArray(loc) && loc.length > 0
              ? String(loc[loc.length - 1])
              : null;
          if (field && field !== "body") {
            // Soften common pydantic email wording
            if (/email/i.test(field) || /email/i.test(msg)) {
              return "Enter a valid email address.";
            }
            return `${field}: ${msg}`;
          }
          return msg;
        }
        return null;
      })
      .filter((p): p is string => !!p);
    if (parts.length > 0) {
      // Dedupe identical messages
      return [...new Set(parts)].join(" ");
    }
  }
  return fallback;
}

/** Lightweight client-side email shape check (not a full RFC parser). */
export function isValidEmailShape(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

/** apiFetchServer is an alias for server-side usage (same implementation, clearer call-site intent). */
export const apiFetchServer = apiFetch;

export async function apiFetch<T = void>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const { token, body, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(fetchOptions.headers as Record<string, string> | undefined),
  };
  // Only set JSON content-type when sending a body (avoids odd DELETE quirks).
  if (body !== undefined && body !== null && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(`${getApiBase()}${path}`, {
      ...fetchOptions,
      body,
      headers,
    });
  } catch {
    throw new ApiError("Something went wrong. Please try again.", 0);
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    const message = formatApiDetail(
      (error as { detail?: unknown }).detail,
      `API error ${res.status}`,
    );
    const code =
      typeof (error as { code?: unknown }).code === "string"
        ? (error as { code: string }).code
        : undefined;
    throw new ApiError(message, res.status, code);
  }

  // 204/205/304 or empty body — do not call res.json() (throws / odd DOMExceptions).
  if (res.status === 204 || res.status === 205 || res.status === 304) {
    return undefined as T;
  }
  const text = await res.text();
  if (!text.trim()) {
    return undefined as T;
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError("Something went wrong. Please try again.", res.status);
  }
}
