import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'purple';
  size?: 'sm' | 'md';
  showDot?: boolean;
  className?: string;
  title?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  showDot = false,
  className = '',
  title
}) => {
  return (
    <span
      title={title}
      data-variant={variant}
      data-size={size}
      className={`console-badge ${className}`}
    >
      {showDot && (
        <span aria-hidden="true" className="w-1.5 h-1.5 rounded-full shrink-0 bg-current" />
      )}
      <span>{children}</span>
    </span>
  );
};
