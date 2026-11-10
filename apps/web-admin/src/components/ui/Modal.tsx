import React, { useEffect, useRef, useId } from 'react';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
}

const maxWidthMap = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '3xl': 'max-w-3xl',
  '4xl': 'max-w-4xl'
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = 'lg'
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  useEffect(() => {
    if (!isOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialogRef.current?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      const items = dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), select, textarea, [tabindex="0"]');
      if (!items?.length) { event.preventDefault(); return; }
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', trap);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', trap); previous?.focus(); };
  }, [isOpen]);
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/70 transition-opacity animate-in fade-in duration-150"
      />

      {/* Modal Dialog */}
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={title ? titleId : undefined}
        aria-describedby={description ? descriptionId : undefined} tabIndex={-1}
        className={`relative w-full ${maxWidthMap[maxWidth]} bg-slate-900 border border-slate-700 rounded shadow-xl z-10 overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-150`}
      >
        {/* Header */}
        {(title || description) && (
          <div className="px-5 py-3.5 border-b border-slate-800 flex items-start justify-between gap-4 shrink-0 bg-slate-900">
            <div>
              {title && <h3 id={titleId} className="text-base font-semibold text-white">{title}</h3>}
              {description && <p id={descriptionId} className="text-sm text-slate-400 mt-0.5">{description}</p>}
            </div>
            <button
              onClick={onClose}
              type="button"
              className="app-button shrink-0 !p-2 min-w-10"
              aria-label="Đóng hộp thoại"
              title="Đóng (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Content Body */}
        <div className="px-4 sm:px-6 py-4 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  );
};
