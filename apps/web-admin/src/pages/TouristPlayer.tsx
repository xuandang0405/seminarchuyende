import { useState } from 'react';
import { createPortal } from 'react-dom';
import { Pause, Play, Square, Volume2 } from 'lucide-react';
import { languages } from '../../../../shared/brand';
import type { useTouristNarration } from './useTouristNarration';
import type { publicUi } from '../i18n/publicUi';

const clock = (value: number) => `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, '0')}`;

export function TouristPlayer({
  narration,
  ui,
  dock,
}: {
  narration: ReturnType<typeof useTouristNarration>;
  ui: ReturnType<typeof publicUi>;
  dock?: HTMLDivElement | null;
}) {
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const track = narration.track!;
  const toggle = () => {
    const audio = narration.audio.current;
    if (!audio) return;
    if (audio.paused) void audio.play().catch(() => {});
    else audio.pause();
  };

  const langLabel = languages.find(([code]) => code === track.lang)?.[1] || track.lang;
  const media = <audio
    hidden
    ref={narration.audio}
    src={track.url}
    {...narration.mediaEvents}
    onLoadedMetadata={event => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
    onPlaying={() => { setPlaying(true); narration.mediaEvents.onPlaying(); }}
    onPause={() => { setPlaying(false); narration.mediaEvents.onPause(); }}
    onTimeUpdate={event => { setPosition(event.currentTarget.currentTime); narration.mediaEvents.onTimeUpdate(); }}
  />;

  if (dock) {
    return <>{media}{createPortal(
      <div className="tv-player-mini tv-glass-dark" role="region" aria-label="Thuyết minh đang phát" aria-live="polite">
        <div className={`tv-player-eq ${playing ? 'is-playing' : ''}`} aria-hidden="true">
          <span className="tv-eq-bar tv-eq-1" />
          <span className="tv-eq-bar tv-eq-2" />
          <span className="tv-eq-bar tv-eq-3" />
          <span className="tv-eq-bar tv-eq-4" />
        </div>

        <div className="tv-player-mini-info">
          <span className="tv-player-mini-kicker">{narration.requiresTap ? 'Chạm Phát để bắt đầu' : langLabel}</span>
          <strong className="tv-player-mini-title">{track.place.name}</strong>
        </div>

        <button
          type="button"
          className="tv-btn-mini-play"
          onClick={toggle}
          aria-label={playing ? ui.pause : ui.play}
        >
          {playing ? <Pause size={16} /> : <Play size={16} className="translate-x-0.5" />}
        </button>

        <button
          type="button"
          className="tv-btn-mini-stop"
          onClick={() => narration.stop()}
          aria-label={ui.stop}
          title={ui.stop}
        >
          <Square size={12} />
        </button>
      </div>, dock)}</>;
  }

  return <>{media}
    <section className="tv-player tv-player-island" aria-label="Trình phát thuyết minh" role="region" aria-live="polite">
      {/* 4-bar Equalizer animation */}
      <div className={`tv-player-eq ${playing ? 'is-playing' : ''}`} aria-hidden="true" title="Audio Equalizer">
        <span className="tv-eq-bar tv-eq-1" />
        <span className="tv-eq-bar tv-eq-2" />
        <span className="tv-eq-bar tv-eq-3" />
        <span className="tv-eq-bar tv-eq-4" />
      </div>

      <div className="tv-player-info">
        <div className="tv-player-meta">
          <span className="tv-player-badge">
            <Volume2 size={12} aria-hidden="true" /> Giọng HD · {langLabel}
          </span>
          {narration.requiresTap && <span className="tv-player-hint" role="status">Chạm Phát để bắt đầu</span>}
        </div>
        <strong className="tv-player-name">{track.place.name}</strong>
      </div>

      <div className="tv-player-controls">
        <button
          type="button"
          className="tv-btn-play-pause"
          onClick={toggle}
          aria-label={playing ? ui.pause : ui.play}
        >
          {playing ? <Pause size={18} /> : <Play size={18} className="translate-x-0.5" />}
        </button>

        <div className="tv-player-scrub">
          <span className="tv-player-time">{clock(position)}</span>
          <input
            aria-label="Vị trí phát"
            type="range"
            min={0}
            max={duration || 1}
            step="any"
            value={Math.min(position, duration)}
            disabled={!duration}
            onChange={event => {
              if (!narration.audio.current) return;
              narration.audio.current.currentTime = Number(event.target.value);
              setPosition(Number(event.target.value));
            }}
          />
          <span className="tv-player-time">{clock(duration)}</span>
        </div>

        <button
          type="button"
          className="tv-btn-stop"
          onClick={() => narration.stop()}
          aria-label={ui.stop}
          title={ui.stop}
        >
          <Square size={14} />
        </button>
      </div>
    </section>
  </>;
}
