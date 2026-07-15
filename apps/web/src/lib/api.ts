function getApiBase(): string {
  if (typeof window === "undefined") {
    return (
      process.env.API_INTERNAL_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:8000"
    );
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
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

export async function apiFetch<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...fetchOptions.headers,
  };

  let res: Response;
  try {
    res = await fetch(`${getApiBase()}${path}`, {
      ...fetchOptions,
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

  return res.json() as Promise<T>;
}
