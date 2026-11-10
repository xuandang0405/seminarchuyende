import React from 'react';

export interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  action,
  icon,
  className = ''
}) => {
  return (
    <div
      className={`console-empty text-center py-9 px-4 flex flex-col items-center justify-center ${className}`}
    >
      {icon && (
        <div className="w-11 h-11 rounded-xl bg-slate-800 text-indigo-400 flex items-center justify-center mb-3">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      {description && <p className="text-sm text-slate-400 mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};
