import React from 'react';
import { cn } from '@/lib/utils';

interface GlassButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

export const GlassButton = React.forwardRef<HTMLButtonElement, GlassButtonProps>(
  ({ children, variant = 'primary', size = 'md', loading = false, className, disabled, ...props }, ref) => {
    const variantClasses = {
      primary: 'glass-button',
      secondary: 'border border-white/20 bg-white/5 text-white hover:bg-white/10 hover:border-white/40',
      outline: 'border border-white/30 bg-transparent text-white hover:bg-white/5',
    };

    const sizeClasses = {
      sm: 'px-4 py-2 text-sm',
      md: 'px-6 py-3 text-base',
      lg: 'px-8 py-4 text-lg',
    };

    return (
      <button
        ref={ref}
        disabled={loading || disabled}
        className={cn(
          'relative rounded-lg font-semibold transition-all duration-300 flex items-center justify-center gap-2',
          variantClasses[variant],
          sizeClasses[size],
          (loading || disabled) && 'opacity-50 cursor-not-allowed',
          className
        )}
        {...props}
      >
        {loading && (
          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        )}
        {children}
      </button>
    );
  }
);

GlassButton.displayName = 'GlassButton';
