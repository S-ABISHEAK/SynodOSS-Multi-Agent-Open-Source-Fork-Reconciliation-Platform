import React from 'react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Agents are deliberating...',
  size = 'md',
  className,
}) => {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
  };

  return (
    <div className={cn('flex flex-col items-center justify-center gap-4', className)}>
      <div className={cn('relative', sizeClasses[size])}>
        {/* Outer rotating ring */}
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-indigo-400 border-r-indigo-400 animate-spin" />
        
        {/* Inner pulsing circle */}
        <div className="absolute inset-2 rounded-full border border-indigo-500/30 bg-indigo-500/5 pulse-glow" />
      </div>
      {message && (
        <p className="text-sm text-white/60 font-medium">{message}</p>
      )}
    </div>
  );
};
