import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useLocation } from 'wouter';
import { AnimatedLogo } from './AnimatedLogo';
import { useTheme } from '@/contexts/ThemeContext';
import { Github, Moon, Sun, User, Menu, Shield } from 'lucide-react';

const navItems = [
  { label: 'Dashboard', href: '/' },
  { label: 'Governance', href: '/governance', icon: <Shield size={13} className="inline mr-1 -mt-0.5" /> },
];

export const FloatingNav: React.FC = () => {
  const [location, navigate] = useLocation();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <motion.nav
      className="fixed top-0 left-1/2 transform -translate-x-1/2 z-50 mt-4"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <motion.div
        className={`glass rounded-2xl transition-all duration-300 ${
          isScrolled ? 'h-14 shadow-2xl' : 'h-17'
        }`}
        style={{ width: 'clamp(300px, 90vw, 1500px)' }}
        animate={{
          backdropFilter: isScrolled ? 'blur(40px)' : 'blur(30px)',
        }}
      >
        <div className="h-full px-6 flex items-center justify-between">
          {/* Left: Logo + Brand */}
          <motion.div
            className="flex items-center gap-3"
            whileHover={{ scale: 1.05 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            <AnimatedLogo />
            <div className="flex flex-col">
              <span className="text-sm font-bold text-foreground">SynodOSS</span>
              <span className="text-xs text-muted-foreground">v1.0</span>
            </div>
          </motion.div>

          {/* Center: Navigation (hidden on mobile) */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <motion.button
                key={item.href}
                onClick={() => navigate(item.href)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location === item.href
                    ? 'text-cyan-400 bg-cyan-500/10'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {item.label}
              </motion.button>
            ))}
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-3">
            {/* GitHub */}
            <motion.a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg hover:bg-white/5 dark:hover:bg-white/5 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <Github size={18} className="text-muted-foreground hover:text-foreground" />
            </motion.a>

            {/* Theme Toggle */}
            <motion.button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-white/5 dark:hover:bg-white/5 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              {theme === 'dark' ? (
                <Sun size={18} className="text-muted-foreground hover:text-yellow-400" />
              ) : (
                <Moon size={18} className="text-muted-foreground hover:text-blue-400" />
              )}
            </motion.button>

            {/* Profile */}
            <motion.button
              className="p-2 rounded-lg hover:bg-white/5 dark:hover:bg-white/5 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <User size={18} className="text-muted-foreground hover:text-foreground" />
            </motion.button>

            {/* Mobile Menu Toggle */}
            <motion.button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-white/5 dark:hover:bg-white/5 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <Menu size={18} className="text-muted-foreground hover:text-foreground" />
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Mobile Menu */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{
          opacity: isMobileMenuOpen ? 1 : 0,
          y: isMobileMenuOpen ? 0 : -10,
          pointerEvents: isMobileMenuOpen ? 'auto' : 'none',
        }}
        transition={{ duration: 0.2 }}
        className="absolute top-full left-1/2 transform -translate-x-1/2 mt-3 glass rounded-xl p-3 w-48"
      >
        {navItems.map((item) => (
          <motion.button
            key={item.href}
            onClick={() => {
              navigate(item.href);
              setIsMobileMenuOpen(false);
            }}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              location === item.href
                ? 'text-cyan-400 bg-cyan-500/10'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
            }`}
            whileHover={{ x: 4 }}
          >
            {item.label}
          </motion.button>
        ))}
      </motion.div>
    </motion.nav>
  );
};
