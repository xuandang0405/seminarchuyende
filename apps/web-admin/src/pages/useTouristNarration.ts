import { useEffect, useRef, useState } from 'react';
import { getOfflineAudio } from '../services/offline';
import { trackNarration } from '../services/analytics';
import { newRequestId, reportWebListen } from '../services/liveTelemetry';
import { ApiError } from '../services/apiClient';
import { requestNarration } from '../services/narration';
import { placeId, type Place } from './TouristLeaflet';

interface Intent {
  place: Place;
  tourId?: string;
  source: 'manual' | 'gps' | 'qr';
  key?: string;
  consent?: boolean;
}
interface Track {
  id?: string;
  grantToken?: string;
  place: Place;
  url: string;
  lang: string;
}

export function useTouristNarration({ userId, lang, online, onStop, onComplete }: {
  userId?: string; lang: string; online: boolean; onStop: (id: string) => void; onComplete: (id: string) => void;
}) {
  const audio = useRef<HTMLAudioElement>(null);
  const current = useRef<Track | null>(null);
  const request = useRef<AbortController>();
  const active = useRef(false);
  const started = useRef(false);
  const reportedMs = useRef(0);
  const [track, setTrack] = useState<Track | null>(null);
  const [busy, setBusy] = useState<Place | null>(null);
  const [trial, setTrial] = useState<Intent | null>(null);
  const [error, setError] = useState<{ message: string; placeId: string } | null>(null);
  const [gateTourId, setGateTourId] = useState('');
  const [gateReason, setGateReason] = useState<'' | 'trial-used' | 'ticket'>('');
  const [requiresTap, setRequiresTap] = useState(false);

  const report = (type: string, delta?: number) => {
    const item = current.current;
    if (item?.id) void trackNarration(type, placeId(item.place), item.id, item.lang, delta);
  };
  const reportProgress = (force: boolean, completed = false) => {
    const track = current.current;
    const played = audio.current?.played;
    if (!started.current || !played || !track?.grantToken) return;
    let seconds = 0;
    for (let index = 0; index < played.length; index++) seconds += played.end(index) - played.start(index);
    const listenedMs = Math.round(seconds * 1000);
    const delta = Math.min(15000, listenedMs - reportedMs.current);
    if (!force && delta < 2000) return;
    if (delta > 0) {
      report('narration_progress', delta);
      reportedMs.current += delta;
    }
    void reportWebListen(track.grantToken, listenedMs, completed);
  };
  const reset = () => {
    request.current?.abort();
    if (current.current?.url.startsWith('blob:')) URL.revokeObjectURL(current.current.url);
    audio.current?.pause();
    current.current = null;
    active.current = false;
    started.current = false;
    reportedMs.current = 0;
  };
  const stop = (complete = false) => {
    const place = current.current?.place || busy;
    if (started.current) {
      reportProgress(true, complete);
      report(complete ? 'narration_completed' : 'narration_stopped');
    }
    if (place) (complete ? onComplete : onStop)(placeId(place));
    reset();
    setTrack(null); setBusy(null); setRequiresTap(false);
  };
  useEffect(() => {
    const pageHide = () => reportProgress(true);
    window.addEventListener('pagehide', pageHide);
    return () => {
      window.removeEventListener('pagehide', pageHide);
      reportProgress(true);
      reset();
    };
  }, []);
  useEffect(() => {
    stop(); setTrial(null); setError(null); setGateTourId(''); setGateReason('');
  }, [userId, lang]);
  useEffect(() => {
    if (!track) return;
    const player = audio.current;
    player?.play().catch(() => { if (current.current === track) setRequiresTap(true); });
  }, [track]);

  const play = async (intent: Intent) => {
    if (active.current && intent.source === 'gps') return;
    stop();
    setTrial(null); setError(null); setGateTourId(''); setGateReason('');
    active.current = true;
    setBusy(intent.place);
    const controller = new AbortController();
    request.current = controller;
    const id = placeId(intent.place);
    const key = intent.key || newRequestId();
    try {
      const grant = online ? await requestNarration(id, lang, {
        tourId: intent.tourId, source: intent.source, consent: intent.consent, signedIn: Boolean(userId),
        key, signal: controller.signal,
      }).catch(error => {
        if (error instanceof ApiError && [0, 502, 503, 504].includes(error.statusCode)) return null;
        throw error;
      }) : null;
      const saved = !grant && !controller.signal.aborted ? await getOfflineAudio(userId, lang, id, intent.tourId) : null;
      if (controller.signal.aborted) {
        if (saved) URL.revokeObjectURL(saved.url);
        return;
      }
      if (!grant && !saved) throw new Error('Không kết nối được máy chủ. Điểm này chưa có thuyết minh ngoại tuyến.');
      const item = { place: intent.place, id: grant?.playback_id, grantToken: grant?.grant_token,
        url: grant?.stream_url || saved!.url, lang: grant?.lang || saved!.lang };
      current.current = item;
      setTrack(item);
    } catch (failure) {
      if (controller.signal.aborted) return;
      const detail = failure instanceof ApiError ? failure.details?.detail : undefined;
      if (detail?.error_code === 'TRIAL_CONSENT_REQUIRED') {
        setTrial({ ...intent, tourId: intent.tourId || detail.tour_id, key });
      } else if (detail?.tour_id && ['TRIAL_EXHAUSTED', 'TOUR_PURCHASE_REQUIRED'].includes(detail.error_code)) {
        setGateTourId(detail.tour_id);
        setGateReason(detail.error_code === 'TRIAL_EXHAUSTED' ? 'trial-used' : 'ticket');
      } else {
        setError({ message: (failure as Error).message, placeId: id });
      }
      if (intent.source === 'gps') onStop(id);
      active.current = false;
    } finally { if (!controller.signal.aborted) setBusy(null); }
  };

  return {
    track, busy, trial, error, gateTourId, gateReason, requiresTap, audio, active, play, stop,
    decline: () => setTrial(null),
    dismissGate: () => { setGateTourId(''); setGateReason(''); },
    mediaEvents: {
      onPlaying: () => {
        setRequiresTap(false);
        if (!started.current) {
          started.current = true;
          report('narration_started');
          const grantToken = current.current?.grantToken;
          if (grantToken) void reportWebListen(grantToken, 0);
        }
      },
      onTimeUpdate: () => reportProgress(false),
      onPause: () => reportProgress(true),
      onEnded: () => stop(true),
      onError: () => {
        if (current.current) {
          const id = placeId(current.current.place);
          stop();
          setError({ message: 'Không mở được bản thuyết minh. Vui lòng thử lại.', placeId: id });
        }
      },
    },
  };
}
