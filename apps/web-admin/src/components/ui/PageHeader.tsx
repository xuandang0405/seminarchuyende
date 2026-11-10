import React from 'react';

export interface PageHeaderProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  badge,
  actions,
  className = ''
}) => {
  return (
    <div className={`console-page-heading ${className}`}>
      <div>
        <div className="flex items-center gap-3 flex-wrap">
          <h1>{title}</h1>
          {badge}
        </div>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2.5 shrink-0 flex-wrap">{actions}</div>}
    </div>
  );
};
