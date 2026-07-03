import React from 'react';
import { Link } from 'wouter';
import { cn } from '@/lib/utils';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  showLogo?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  showLogo = true,
}) => {
  return (
    <header className="sticky top-0 z-50 glass-card border-b border-white/10 bg-white/5 backdrop-blur-xl">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/">
          <a className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            {showLogo && (
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-emerald-500 flex items-center justify-center">
                <span className="text-white font-bold text-lg">◆</span>
              </div>
            )}
            <div>
              <h1 className="text-xl font-bold gradient-text">SynodOSS</h1>
              {subtitle && <p className="text-xs text-white/50">{subtitle}</p>}
            </div>
          </a>
        </Link>
        
        {title && (
          <div className="flex-1 ml-8">
            <h2 className="text-lg font-semibold text-white">{title}</h2>
          </div>
        )}
      </div>
    </header>
  );
};
