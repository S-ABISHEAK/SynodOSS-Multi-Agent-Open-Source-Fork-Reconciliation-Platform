import React from 'react';
import { cn } from '@/lib/utils';

interface GlassBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'critical' | 'high' | 'medium' | 'low' | 'advocate' | 'defender' | 'architect' | 'judge';
}

export const GlassBadge = React.forwardRef<HTMLDivElement, GlassBadgeProps>(
  ({ children, variant = 'low', className, ...props }, ref) => {
    const variantClasses = {
      critical: 'badge-critical',
      high: 'badge-high',
      medium: 'badge-medium',
      low: 'badge-low',
      advocate: 'agent-advocate',
      defender: 'agent-defender',
      architect: 'agent-architect',
      judge: 'agent-judge',
    };

    return (
      <div
        ref={ref}
        className={cn('glass-badge', variantClasses[variant], className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

GlassBadge.displayName = 'GlassBadge';
