import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  hoverEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  hoverEffect = false
}) => {
  return (
    <div
      className={`console-panel p-4 sm:p-5 transition-colors duration-150 ${
        hoverEffect ? 'hover:border-slate-700' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<{
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}> = ({ title, description, action, className = '' }) => {
  return (
    <div className={`flex items-start justify-between gap-3 pb-3 mb-4 border-b border-slate-800/80 ${className}`}>
      <div className="min-w-0">
        <h2 className="text-base font-bold text-white tracking-tight">{title}</h2>
        {description && <p className="text-sm text-slate-400 mt-1">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
};
