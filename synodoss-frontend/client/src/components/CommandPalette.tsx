import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, GitBranch, Zap, Settings, HelpCircle, X } from 'lucide-react';
import { useLocation } from 'wouter';

interface Command {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  category: string;
}

export const CommandPalette: React.FC = () => {
  const [, navigate] = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const commands: Command[] = [
    {
      id: '1',
      label: 'Go to Dashboard',
      description: 'Return to main dashboard',
      icon: <GitBranch size={16} />,
      action: () => {
        navigate('/');
        setIsOpen(false);
      },
      category: 'Navigation',
    },
    {
      id: '2',
      label: 'Start New Scan',
      description: 'Begin a new repository scan',
      icon: <Zap size={16} />,
      action: () => {
        navigate('/');
        setIsOpen(false);
      },
      category: 'Actions',
    },
    {
      id: '3',
      label: 'Settings',
      description: 'Open application settings',
      icon: <Settings size={16} />,
      action: () => setIsOpen(false),
      category: 'System',
    },
    {
      id: '4',
      label: 'Help & Documentation',
      description: 'View help documentation',
      icon: <HelpCircle size={16} />,
      action: () => setIsOpen(false),
      category: 'Help',
    },
  ];

  const filteredCommands = commands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(search.toLowerCase()) ||
      cmd.description.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + K to open
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(!isOpen);
        setSearch('');
        setSelectedIndex(0);
      }

      // Close on Escape
      if (e.key === 'Escape') {
        setIsOpen(false);
      }

      // Arrow navigation
      if (isOpen) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setSelectedIndex((prev) => (prev + 1) % filteredCommands.length);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, search, selectedIndex, filteredCommands]);

  return (
    <>
      {/* Keyboard Shortcut Hint */}
      <motion.button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-8 right-8 z-40 flex items-center gap-2 px-4 py-2 glass rounded-lg text-sm text-gray-400 hover:text-white transition-colors"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Search size={16} />
        <span className="hidden md:inline">Ctrl K</span>
      </motion.button>

      {/* Command Palette */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
            />

            {/* Palette */}
            <motion.div
              className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl z-50"
              initial={{ opacity: 0, scale: 0.95, y: -20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
              <div className="glass rounded-2xl overflow-hidden shadow-2xl">
                {/* Search Input */}
                <div className="flex items-center gap-3 px-6 py-4 border-b border-white/10">
                  <Search size={20} className="text-gray-500" />
                  <input
                    type="text"
                    placeholder="Type a command or search..."
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      setSelectedIndex(0);
                    }}
                    autoFocus
                    className="flex-1 bg-transparent text-white placeholder-gray-500 focus:outline-none text-lg"
                  />
                  <motion.button
                    onClick={() => setIsOpen(false)}
                    className="p-1 hover:bg-white/10 rounded-lg transition-colors"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <X size={18} className="text-gray-400" />
                  </motion.button>
                </div>

                {/* Commands List */}
                <div className="max-h-96 overflow-y-auto">
                  {filteredCommands.length === 0 ? (
                    <div className="px-6 py-12 text-center">
                      <p className="text-gray-400">No commands found</p>
                    </div>
                  ) : (
                    <div className="p-2">
                      {filteredCommands.map((cmd, index) => (
                        <motion.button
                          key={cmd.id}
                          onClick={() => {
                            cmd.action();
                            setIsOpen(false);
                          }}
                          className={`w-full flex items-start gap-3 px-4 py-3 rounded-lg transition-colors ${
                            index === selectedIndex ? 'bg-indigo-500/20 border border-indigo-500/30' : 'hover:bg-white/5'
                          }`}
                          whileHover={{ x: 4 }}
                        >
                          <div className="p-2 rounded-lg bg-white/5 text-indigo-400 flex-shrink-0">{cmd.icon}</div>
                          <div className="flex-1 text-left">
                            <p className="text-sm font-semibold text-white">{cmd.label}</p>
                            <p className="text-xs text-gray-400">{cmd.description}</p>
                          </div>
                          <span className="text-xs text-gray-500 flex-shrink-0">{cmd.category}</span>
                        </motion.button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="px-6 py-3 border-t border-white/10 flex items-center justify-between text-xs text-gray-500">
                  <div className="flex gap-2">
                    <kbd className="px-2 py-1 bg-white/10 rounded">↑↓</kbd>
                    <span>Navigate</span>
                    <kbd className="px-2 py-1 bg-white/10 rounded ml-2">Enter</kbd>
                    <span>Select</span>
                  </div>
                  <kbd className="px-2 py-1 bg-white/10 rounded">Esc</kbd>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};
