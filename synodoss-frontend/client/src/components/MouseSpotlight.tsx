import React, { useEffect, useRef } from 'react';

export const MouseSpotlight: React.FC = () => {
  const spotlightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!spotlightRef.current) return;

      const x = e.clientX;
      const y = e.clientY;

      spotlightRef.current.style.background = `radial-gradient(circle 600px at ${x}px ${y}px, rgba(59, 130, 246, 0.15), transparent 80%)`;
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div
      ref={spotlightRef}
      className="fixed inset-0 pointer-events-none z-30 transition-all duration-300"
      style={{
        background: 'radial-gradient(circle 600px at 50% 50%, rgba(59, 130, 246, 0.1), transparent 80%)',
      }}
    />
  );
};
