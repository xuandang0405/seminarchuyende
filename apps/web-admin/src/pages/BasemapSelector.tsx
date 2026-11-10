import { useEffect, useRef, useState } from 'react';
import { Check, Download, Layers, Map, X } from 'lucide-react';
import { BASEMAP_STYLES, getSavedBasemap, saveBasemap, type BasemapId } from '../services/mapStyles';
import type { ActiveMapPack, MapMode } from '../services/mapPack';

interface BasemapSelectorProps {
  open: boolean;
  onClose: () => void;
  currentMode: MapMode;
  onSelectMode: (mode: MapMode) => void;
  installedPack: ActiveMapPack | null;
  online: boolean;
}

export function BasemapSelector({ open, onClose, currentMode, onSelectMode, installedPack, online }: BasemapSelectorProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState<BasemapId>(getSavedBasemap);

  useEffect(() => {
    const modal = dialog.current;
    if (!modal) return;
    if (open && !modal.open) modal.showModal();
    if (!open && modal.open) modal.close();
  }, [open]);

  function choose(id: BasemapId) {
    setSelected(id);
    saveBasemap(id);
    onSelectMode('hybrid');
    onClose();
  }

  return (
    <dialog ref={dialog} className="tv-basemap-dialog" aria-labelledby="tv-basemap-title"
      onCancel={onClose} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="tv-basemap-content">
        <header className="tv-basemap-heading">
          <span className="tv-basemap-icon"><Layers size={22} aria-hidden="true" /></span>
          <div><h2 id="tv-basemap-title">Kiểu bản đồ</h2><p>Chọn bản đồ phù hợp với chuyến đi.</p></div>
          <button type="button" autoFocus className="tv-basemap-close" onClick={onClose} aria-label="Đóng"><X size={21} /></button>
        </header>
        {BASEMAP_STYLES.map(style => {
          const active = currentMode !== 'offline' && selected === style.id;
          return <button key={style.id} type="button" className="tv-basemap-option" data-active={active}
            aria-pressed={active} disabled={!online && style.id !== 'district'} onClick={() => choose(style.id)}>
            <span className="tv-basemap-icon" data-style={style.id}><Map size={22} aria-hidden="true" /></span>
            <span><strong>{style.name}</strong><small>{style.description}</small></span>
            {active && <Check size={18} aria-hidden="true" />}
          </button>;
        })}
        <button type="button" className="tv-basemap-option" data-active={currentMode === 'offline'}
          aria-pressed={currentMode === 'offline'} onClick={() => { onSelectMode('offline'); onClose(); }}>
          <span className="tv-basemap-icon"><Download size={21} aria-hidden="true" /></span>
          <span><strong>Ngoại tuyến</strong><small>{installedPack ? 'Dùng gói bản đồ Quận 4 đã lưu.' : 'Dùng bản đồ Quận 4 có sẵn.'}</small></span>
          {currentMode === 'offline' && <Check size={18} aria-hidden="true" />}
        </button>
      </div>
    </dialog>
  );
}
