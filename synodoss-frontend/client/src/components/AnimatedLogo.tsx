import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

export const AnimatedLogo: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = React.useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left - rect.width / 2) / 20;
      const y = (e.clientY - rect.top - rect.height / 2) / 20;
      setMousePosition({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div ref={containerRef} className="relative w-10 h-10">
      {/* Outer rotating ring */}
      <motion.div
        className="absolute inset-0"
        animate={{ rotateZ: 360 }}
        transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        style={{
          perspective: '1000px',
          rotateX: mousePosition.y,
          rotateY: mousePosition.x,
        }}
      >
        <svg
          viewBox="0 0 40 40"
          className="w-full h-full"
          fill="none"
          stroke="url(#gradient1)"
          strokeWidth="1.5"
        >
          <defs>
            <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
          </defs>
          {/* Git graph nodes */}
          <circle cx="20" cy="10" r="2" fill="#3b82f6" />
          <circle cx="28" cy="18" r="2" fill="#06b6d4" />
          <circle cx="20" cy="26" r="2" fill="#10b981" />
          <circle cx="12" cy="18" r="2" fill="#8b5cf6" />
          
          {/* Connection lines */}
          <line x1="20" y1="10" x2="28" y2="18" strokeOpacity="0.6" />
          <line x1="28" y1="18" x2="20" y2="26" strokeOpacity="0.6" />
          <line x1="20" y1="26" x2="12" y2="18" strokeOpacity="0.6" />
          <line x1="12" y1="18" x2="20" y2="10" strokeOpacity="0.6" />
        </svg>
      </motion.div>

      {/* Inner pulsing core */}
      <motion.div
        className="absolute inset-2 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500"
        animate={{
          boxShadow: [
            '0 0 10px rgba(59, 130, 246, 0.3)',
            '0 0 20px rgba(59, 130, 246, 0.6)',
            '0 0 10px rgba(59, 130, 246, 0.3)',
          ],
        }}
        transition={{ duration: 3, repeat: Infinity }}
      />

      {/* Glow effect */}
      <motion.div
        className="absolute inset-0 rounded-lg bg-gradient-to-br from-indigo-500/20 to-cyan-500/20 blur-md"
        animate={{
          opacity: [0.3, 0.6, 0.3],
        }}
        transition={{ duration: 3, repeat: Infinity }}
      />
    </div>
  );
};
