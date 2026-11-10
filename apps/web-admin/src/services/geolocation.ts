const MAX_FIX_AGE = 30000;
export const ROUTE_ACCURACY = 100;

export function usableFix(sample: GeolocationPosition) {
  const { latitude, longitude, accuracy } = sample.coords;
  const age = Date.now() - sample.timestamp;
  return Number.isFinite(latitude) && Math.abs(latitude) <= 90 &&
    Number.isFinite(longitude) && Math.abs(longitude) <= 180 &&
    Number.isFinite(accuracy) && accuracy >= 0 && age >= -1000 && age <= MAX_FIX_AGE;
}

export function gpsError(code: number, detail = '') {
  if (!window.isSecureContext) return 'Địa chỉ hiện tại dùng HTTP. Mở localhost trên máy chủ hoặc dùng HTTPS để định vị.';
  if (!navigator.geolocation) return 'Trình duyệt này chưa hỗ trợ định vị.';
  if (code === 1 && !/system|platform|windows/i.test(detail)) {
    return 'Quyền vị trí bị chặn. Mở cài đặt của trang cạnh thanh địa chỉ, chọn Vị trí → Cho phép, rồi thử lại.';
  }
  if (/windows/i.test(navigator.userAgent)) {
    return 'Windows chưa cung cấp vị trí. Kiểm tra Dịch vụ vị trí trong Cài đặt và Geolocation Service trong Services.';
  }
  return 'Thiết bị chưa gửi được vị trí. Bật dịch vụ vị trí và quyền vị trí chính xác cho trình duyệt rồi thử lại.';
}

export function readCurrentPosition(
  signal: AbortSignal,
  { targetAccuracy = 35, timeout = 12000 } = {},
): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(signal.reason); return; }
    if (!window.isSecureContext || !navigator.geolocation) {
      reject(new Error(gpsError(1)));
      return;
    }
    let best: GeolocationPosition | undefined;
    let watch: number | undefined;
    let deadline: number | undefined;
    let fallbackTimer: number | undefined;
    let fallbackStarted = false;
    let unavailable: GeolocationPositionError | undefined;
    let finished = false;
    function finish(error?: unknown) {
      if (finished) return;
      finished = true;
      if (watch !== undefined) navigator.geolocation.clearWatch(watch);
      window.clearTimeout(deadline);
      window.clearTimeout(fallbackTimer);
      signal.removeEventListener('abort', abort);
      if (!error && best) resolve(best);
      else reject(error ?? new Error(gpsError(unavailable?.code ?? 3, unavailable?.message)));
    }
    function abort() { finish(signal.reason); }
    function accept(sample: GeolocationPosition) {
      if (finished || !usableFix(sample)) return;
      if (!best || sample.coords.accuracy < best.coords.accuracy) best = sample;
      if (sample.coords.accuracy <= targetAccuracy) finish();
    }
    function handleError(error: GeolocationPositionError) {
      if (finished) return;
      if (error.code === 1) { finish(new Error(gpsError(1, error.message))); return; }
      if (!unavailable || error.code === 2) unavailable = error;
      tryFallback();
    }
    function tryFallback() {
      if (finished || fallbackStarted) return;
      fallbackStarted = true;
      navigator.geolocation.getCurrentPosition(accept, handleError, {
        enableHighAccuracy: false, maximumAge: 0, timeout: Math.min(7500, timeout),
      });
    }
    signal.addEventListener('abort', abort, { once: true });
    deadline = window.setTimeout(() => finish(), timeout);
    fallbackTimer = window.setTimeout(tryFallback, 2500);
    watch = navigator.geolocation.watchPosition(accept, handleError, {
      enableHighAccuracy: true, maximumAge: 0, timeout,
    });
    if (finished) navigator.geolocation.clearWatch(watch);
  });
}
