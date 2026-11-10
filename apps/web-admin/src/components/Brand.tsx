import { Link } from 'react-router-dom';
import { brandPath, harborArtwork } from '../../../../shared/brand';

const harbor = 'data:image/svg+xml,' + encodeURIComponent(harborArtwork);

export function Brand({ subtitle, to = '/client', onClick }: { subtitle?: string; to?: string; onClick?: () => void }) {
  return <Link to={to} onClick={onClick} className="brand-lockup" aria-label="TourVoice">
    <span className="brand-mark"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d={brandPath} /></svg></span>
    <span><strong>TourVoice</strong>{subtitle && <small>{subtitle}</small>}</span>
  </Link>;
}

export function HarborArt({ className }: { className?: string }) {
  return <img className={className} alt="" src={harbor} width={640} height={360} draggable={false} />;
}
