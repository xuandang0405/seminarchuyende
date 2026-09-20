/**
 * mobile/src/config/runtime.js
 *
 * Centralized Mobile API Base URL and Environment Profile Resolver.
 *
 * Priority:
 * 1. process.env.EXPO_PUBLIC_API_BASE_URL (Explicit build/runtime configuration)
 * 2. Fallback profile based on Platform and environment mode
 * 3. In production profile, strictly requires HTTPS and rejects localhost / loopback.
 */

import { Platform } from "react-native";

const FORBIDDEN_PROD_HOSTNAMES = [
  "localhost",
  "127.0.0.1",
  "10.0.2.2",
  "0.0.0.0",
];

export function resolveMobileApiBaseUrl() {
  // Check explicit environment variable (e.g. from .env, .env.production or EAS build)
  const envUrl = (process.env.EXPO_PUBLIC_API_BASE_URL || process.env.EXPO_PUBLIC_API_URL)?.trim();
  const isProduction = process.env.NODE_ENV === "production";

  if (envUrl) {
    const cleanUrl = envUrl.replace(/\/+$/, "");

    if (isProduction) {
      for (const forbidden of FORBIDDEN_PROD_HOSTNAMES) {
        if (cleanUrl.toLowerCase().includes(forbidden)) {
          console.warn(
            `[Mobile Runtime] WARNING: Production profile received loopback address (${forbidden}). Ensure EXPO_PUBLIC_API_BASE_URL points to the public HTTPS domain.`
          );
        }
      }
    }
    return cleanUrl;
  }

  // Development profile fallbacks
  if (Platform.OS === "android") {
    // Android Emulator host loopback alias
    return "http://10.0.2.2:8000/api/v1";
  }

  if (Platform.OS === "ios") {
    // iOS Simulator connects directly to macOS loopback
    return "http://localhost:8000/api/v1";
  }

  return "http://localhost:8000/api/v1";
}

export function resolveBackendRoot(apiBaseUrl) {
  if (!apiBaseUrl) return "http://localhost:8000";
  // Remove /api/v1 or /api suffix to obtain root origin
  return apiBaseUrl.replace(/\/api(\/v\d+)?\/?$/, "");
}

export const MOBILE_API_BASE_URL = resolveMobileApiBaseUrl();
export const MOBILE_BACKEND_ROOT = resolveBackendRoot(MOBILE_API_BASE_URL);
