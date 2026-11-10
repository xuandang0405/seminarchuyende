import { useEffect, useRef } from 'react';
import { ArrowRight, Headphones, Ticket, X } from 'lucide-react';

export function NarrationDialog({ trialPlace, reason, onConfirm, onDismiss }: {
  trialPlace?: string;
  reason: '' | 'trial-used' | 'ticket';
  onConfirm: () => void;
  onDismiss: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    const previousOverflow = document.body.style.overflow;
    element.showModal();
    document.body.style.overflow = 'hidden';
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const trial = trialPlace !== undefined;
  const Icon = trial ? Headphones : Ticket;
  return <dialog ref={dialog} className="tv-access-dialog" aria-labelledby="narration-access-title"
    aria-describedby="narration-access-description" onCancel={event => { event.preventDefault(); onDismiss(); }}>
    <div className="tv-access-head">
      <span className="tv-access-icon"><Icon size={23} aria-hidden="true" /></span>
      <button type="button" className="tv-btn-sheet-close" aria-label="Đóng" onClick={onDismiss}><X size={20} /></button>
    </div>
    <p className="tv-kicker">{trial ? 'THUYẾT MINH NGHE THỬ' : 'THUYẾT MINH THEO TUYẾN'}</p>
    <h2 id="narration-access-title" className="tv-detail-title">{trial ? 'Dùng một lượt nghe thử?' : reason === 'trial-used' ? 'Đã dùng hết lượt nghe thử' : 'Cần vé để nghe điểm dừng này'}</h2>
    <p id="narration-access-description">{trial
      ? <>Bạn sẽ nghe <strong>{trialPlace}</strong>. Hệ thống tính lượt khi cấp quyền phát.</>
      : 'Mở thông tin tuyến tour để xem giá vé và các điểm thuyết minh.'}</p>
    <div className="tv-access-actions">
      <button type="button" className="tv-btn-action-secondary" onClick={onDismiss}>Để sau</button>
      <button type="button" className="tv-btn-action-primary" onClick={onConfirm}>
        {trial ? 'Đồng ý nghe thử' : 'Xem vé tuyến tour'} <ArrowRight size={16} aria-hidden="true" />
      </button>
    </div>
  </dialog>;
}
