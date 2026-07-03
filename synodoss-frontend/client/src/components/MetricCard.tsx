import React from 'react';
import { GlassCard } from './glass/GlassCard';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  color?: 'indigo' | 'emerald' | 'rose' | 'amber';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  icon,
  color = 'indigo',
  className,
}) => {
  const colorClasses = {
    indigo: 'text-indigo-400',
    emerald: 'text-emerald-400',
    rose: 'text-rose-400',
    amber: 'text-amber-400',
  };

  return (
    <GlassCard className={cn('p-4 flex flex-col gap-2', className)}>
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/60 font-medium">{label}</p>
        {icon && <div className={cn('text-lg', colorClasses[color])}>{icon}</div>}
      </div>
      <div className="flex items-baseline gap-2">
        <span className={cn('text-2xl font-bold', colorClasses[color])}>{value}</span>
        {unit && <span className="text-xs text-white/40">{unit}</span>}
      </div>
    </GlassCard>
  );
};
