import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'purple';
  size?: 'sm' | 'md';
  showDot?: boolean;
  className?: string;
  title?: string;
}

const variantStyles: Record<NonNullable<BadgeProps['variant']>, { container: string; dot: string }> = {
  success: {
    container: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    dot: 'bg-emerald-400'
  },
  warning: {
    container: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    dot: 'bg-amber-400'
  },
  danger: {
    container: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    dot: 'bg-rose-400'
  },
  info: {
    container: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    dot: 'bg-sky-400'
  },
  neutral: {
    container: 'bg-slate-800/80 text-slate-300 border-slate-700/60',
    dot: 'bg-slate-400'
  },
  purple: {
    container: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    dot: 'bg-indigo-400'
  }
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  showDot = false,
  className = '',
  title
}) => {
  const styles = variantStyles[variant];
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border transition-colors select-none ${styles.container} ${sizeClasses} ${className}`}
    >
      {showDot && (
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${styles.dot}`} />
      )}
      <span>{children}</span>
    </span>
  );
};
