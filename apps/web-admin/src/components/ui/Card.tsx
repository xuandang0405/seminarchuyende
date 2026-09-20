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
      className={`bg-slate-900/80 backdrop-blur-sm border border-slate-800/90 rounded-2xl p-6 transition-all duration-200 ${
        hoverEffect ? 'hover:border-slate-700/90 hover:shadow-lg hover:shadow-black/20 hover:-translate-y-0.5' : ''
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
    <div className={`flex items-start justify-between gap-4 pb-4 mb-4 border-b border-slate-800/80 ${className}`}>
      <div>
        <h3 className="text-base font-bold text-white tracking-tight">{title}</h3>
        {description && <p className="text-xs text-slate-400 mt-1">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
};
