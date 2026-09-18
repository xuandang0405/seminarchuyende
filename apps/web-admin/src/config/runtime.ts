/**
 * apps/web-admin/src/config/runtime.ts
 *
 * Centralized API Base URL and Runtime Configuration Resolver for Web Admin.
 *
 * Enforces:
 * 1. Same-origin relative path default (/api/v1) for production.
 * 2. Rejection of localhost / loopback addresses when running in production mode.
 * 3. Normalization of paths to prevent double slashes or duplicated prefixes (/api/v1/api/v1).
 * 4. Safe failure without leaking secrets.
 */

export interface RuntimeConfig {
  mode: string;
  apiBaseUrl: string;
  isProduction: boolean;
}

const FORBIDDEN_PROD_HOSTNAMES = [
  'localhost',
  '127.0.0.1',
  '0.0.0.0',
  'host.docker.internal',
];

/**
 * Validates and resolves the API Base URL.
 */
export function resolveApiBaseUrl(rawEnvUrl?: string, mode?: string): string {
  const currentMode = mode || (import.meta as any)?.env?.MODE || 'production';
  const isProd = currentMode === 'production';

  const configured = (rawEnvUrl || (import.meta as any)?.env?.VITE_API_BASE_URL || '').trim();

  // If not configured, default to standard same-origin relative path
  if (!configured) {
    return '/api/v1';
  }

  // Sanitize trailing slashes
  const cleanUrl = configured.replace(/\/+$/, '');

  // Guard against loopback in production
  if (isProd) {
    for (const forbidden of FORBIDDEN_PROD_HOSTNAMES) {
      if (cleanUrl.toLowerCase().includes(forbidden)) {
        console.error(
          `[RuntimeConfig] CRITICAL: Production environment specified a loopback address (${forbidden}). Falling back to same-origin '/api/v1'.`
        );
        return '/api/v1';
      }
    }
  }

  return cleanUrl;
}

const _apiBaseUrl = resolveApiBaseUrl();

export const runtimeConfig: RuntimeConfig = {
  mode: (import.meta as any)?.env?.MODE || 'production',
  apiBaseUrl: _apiBaseUrl,
  isProduction: ((import.meta as any)?.env?.MODE || 'production') === 'production',
};

/**
 * Builds a clean, fully-qualified endpoint path using the centralized base URL.
 * Automatically handles:
 * - Leading slashes: apiUrl('/auth/login') -> '/api/v1/auth/login'
 * - Redundant prefixes: apiUrl('/api/v1/auth/login') -> '/api/v1/auth/login'
 * - Query strings and parameter concatenation
 */
export function apiUrl(path: string): string {
  if (!path) return runtimeConfig.apiBaseUrl;

  // Already a full external URL
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  let normalized = path.startsWith('/') ? path : `/${path}`;

  // Prevent double /api/v1 prefix
  if (runtimeConfig.apiBaseUrl.endsWith('/api/v1') && normalized.startsWith('/api/v1')) {
    const baseWithoutPrefix = runtimeConfig.apiBaseUrl.slice(0, -'/api/v1'.length);
    return `${baseWithoutPrefix}${normalized}`;
  }

  return `${runtimeConfig.apiBaseUrl}${normalized}`;
}
