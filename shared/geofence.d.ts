export function calculateDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number;
export class GeofenceEngine {
  constructor(options?: { accuracyThresholdMeters?: number; debounceMs?: number; cooldownMs?: number });
  evaluateLocation(location: any, pois: any[]): { poi: any; distance: number; triggerType: string } | null;
  markPlaybackCompleted(id: string): void;
  suppressCurrentZone(id: string): void;
  clearPendingEntries(): void;
  reset(): void;
}
export const geofenceEngine: GeofenceEngine;
