import { ApiErrorPayload, HealthResponse } from '../types';

export class ApiError extends Error {
  public status: number;
  public payload: ApiErrorPayload;

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message || `API request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers: customHeaders, ...customOptions } = options;

  let url = endpoint;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      searchParams.append(key, String(value));
    });
    url += `?${searchParams.toString()}`;
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };

  const method = (customOptions.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
  }

  const response = await fetch(url, {
    credentials: 'same-origin',
    headers: {
      ...headers,
      ...(customHeaders as Record<string, string>),
    },
    ...customOptions,
  });

  if (!response.ok) {
    let payload: ApiErrorPayload;
    try {
      payload = await response.json();
    } catch {
      payload = {
        message: response.statusText || 'An unexpected server error occurred',
      };
    }
    throw new ApiError(response.status, payload);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(url: string, options?: RequestOptions) =>
    request<T>(url, { ...options, method: 'GET' }),
  post: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>(url, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),
  put: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>(url, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>(url, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(url: string, options?: RequestOptions) =>
    request<T>(url, { ...options, method: 'DELETE' }),

  // Service Endpoints
  checkHealth: () => request<HealthResponse>('/api/health/'),
};
