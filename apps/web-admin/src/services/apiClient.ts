/**
 * Core API Client for Web Admin & Client Portal
 * Provides typed REST communication, automatic token injection,
 * unified error normalization, and request/response interceptors.
 */

import { apiUrl } from '../config/runtime';

export interface RequestOptions extends RequestInit {
  token?: string | null;
  params?: Record<string, string | number | boolean | undefined | null>;
}

export class ApiError extends Error {
  public statusCode: number;
  public details: any;

  constructor(message: string, statusCode: number, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Extracts friendly error string from FastAPI error payloads.
 */
function extractErrorMessage(data: any, defaultMsg: string): string {
  if (!data) return defaultMsg;
  if (typeof data === 'string') return data;
  if (data.detail) {
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
    }
    if (typeof data.detail === 'object') {
      return JSON.stringify(data.detail);
    }
  }
  if (data.message) return data.message;
  if (data.error) return data.error;
  return defaultMsg;
}

/**
 * Retrieves the stored authentication token from localStorage.
 */
export function getStoredToken(): string | null {
  return localStorage.getItem('token') || localStorage.getItem('admin_token') || null;
}

/**
 * Centralized fetch handler.
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { token, params, headers, ...restOptions } = options;

  // Build Query String if params provided
  let url = apiUrl(endpoint);
  if (params) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    if (qs) {
      url += (url.includes('?') ? '&' : '?') + qs;
    }
  }

  const effectiveToken = token !== undefined ? token : getStoredToken();
  const currentLang = localStorage.getItem('app_language') || localStorage.getItem('i18nextLng') || 'vi';
  
  const requestHeaders: Record<string, string> = {
    Accept: 'application/json',
    'Accept-Language': currentLang,
    ...(headers as Record<string, string> || {}),
  };

  // Only attach Content-Type: application/json if body is not FormData
  if (!(restOptions.body instanceof FormData) && !requestHeaders['Content-Type']) {
    requestHeaders['Content-Type'] = 'application/json';
  }

  if (effectiveToken) {
    requestHeaders['Authorization'] = `Bearer ${effectiveToken}`;
  }


  try {
    const response = await fetch(url, {
      ...restOptions,
      credentials: 'include',
      headers: requestHeaders,
    });

    // Handle 204 No Content
    if (response.status === 204) {
      return null as unknown as T;
    }

    const contentType = response.headers.get('content-type') || '';
    let responseData: any = null;
    if (contentType.includes('application/json')) {
      responseData = await response.json();
    } else {
      responseData = await response.text();
    }

    if (!response.ok) {
      const errMsg = extractErrorMessage(responseData, `Yêu cầu thất bại (Mã lỗi ${response.status})`);
      throw new ApiError(errMsg, response.status, responseData);
    }

    return responseData as T;
  } catch (error: any) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network / CORS / Fetch Error
    throw new ApiError(
      error.message || 'Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.',
      0,
      error
    );
  }
}

export const apiClient = {
  get: <T = any>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { method: 'GET', ...options }),

  post: <T = any>(endpoint: string, body?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
      ...options,
    }),

  put: <T = any>(endpoint: string, body?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body),
      ...options,
    }),

  patch: <T = any>(endpoint: string, body?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      method: 'PATCH',
      body: body instanceof FormData ? body : JSON.stringify(body),
      ...options,
    }),

  delete: <T = any>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { method: 'DELETE', ...options }),

  upload: <T = any>(endpoint: string, formData: FormData, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      method: 'POST',
      body: formData,
      ...options,
    }),
};
