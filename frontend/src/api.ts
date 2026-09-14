export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let adminToken = sessionStorage.getItem("asm.adminToken") ?? "";

export function setAdminToken(token: string) {
  adminToken = token;
  if (token) sessionStorage.setItem("asm.adminToken", token);
  else sessionStorage.removeItem("asm.adminToken");
}

export function getAdminToken() {
  return adminToken;
}

export async function api<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (adminToken) headers.set("Authorization", `Bearer ${adminToken}`);
  const response = await fetch(url, { ...options, headers });
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : "Control plane operation failed.";
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export async function apiBlob(url: string): Promise<Blob> {
  const headers = new Headers();
  if (adminToken) headers.set("Authorization", `Bearer ${adminToken}`);
  const response = await fetch(url, { headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload && typeof payload.detail === "string" ? payload.detail : "Could not load binary data.";
    throw new ApiError(response.status, detail);
  }
  return response.blob();
}
