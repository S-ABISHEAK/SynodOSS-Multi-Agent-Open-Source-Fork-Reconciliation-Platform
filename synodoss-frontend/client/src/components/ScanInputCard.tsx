import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Github, Zap, Loader, AlertCircle } from 'lucide-react';
import { useLocation } from 'wouter';
import { scanApi, handleApiError } from '@/lib/api';
import { toast } from 'sonner';

export const ScanInputCard: React.FC = () => {
  const [, navigate] = useLocation();
  const [upstreamUrl, setUpstreamUrl] = useState('');
  const [forkUrl, setForkUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartScan = async () => {
    if (!upstreamUrl.trim() || !forkUrl.trim()) {
      setError('Both upstream and fork URLs are required.');
      return;
    }
    setError(null);
    setIsScanning(true);
    try {
      const result = await scanApi.startScan(upstreamUrl.trim(), forkUrl.trim());
      toast.success(`Scan #${result.scan_id} started!`);
      navigate(`/scans/${result.scan_id}`);
    } catch (err) {
      const msg = handleApiError(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <motion.div
      className="glass rounded-2xl p-8 col-span-1 lg:col-span-2"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-foreground mb-2">Repository Scan</h2>
        <p className="text-sm text-muted-foreground">Analyze conflicts between upstream and fork repositories</p>
      </div>

      <div className="space-y-6">
        {/* Upstream Repository */}
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-3">
            Upstream Repository URL
          </label>
          <motion.div className="relative group" whileHover={{ scale: 1.01 }}>
            <div className="absolute left-4 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-indigo-400 transition-colors">
              <Github size={18} />
            </div>
            <input
              type="text"
              value={upstreamUrl}
              onChange={(e) => setUpstreamUrl(e.target.value)}
              disabled={isScanning}
              className="w-full pl-12 pr-4 py-3 glass rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all disabled:opacity-50"
              placeholder="https://github.com/org/upstream-repo"
            />
          </motion.div>
        </div>

        {/* Fork Repository */}
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-3">
            Fork Repository URL
          </label>
          <motion.div className="relative group" whileHover={{ scale: 1.01 }}>
            <div className="absolute left-4 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-indigo-400 transition-colors">
              <Github size={18} />
            </div>
            <input
              type="text"
              value={forkUrl}
              onChange={(e) => setForkUrl(e.target.value)}
              disabled={isScanning}
              className="w-full pl-12 pr-4 py-3 glass rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all disabled:opacity-50"
              placeholder="https://github.com/you/fork-repo"
            />
          </motion.div>
        </div>

        {/* Error message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3"
          >
            <AlertCircle size={16} />
            {error}
          </motion.div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <motion.button
            onClick={handleStartScan}
            disabled={isScanning}
            className="flex-1 relative group overflow-hidden rounded-lg py-3 font-semibold transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            whileHover={{ scale: isScanning ? 1 : 1.02 }}
            whileTap={{ scale: isScanning ? 1 : 0.98 }}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-blue-600 group-hover:from-indigo-500 group-hover:to-blue-500 transition-all" />
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity blur-xl bg-gradient-to-r from-indigo-600 to-blue-600" />
            <div className="relative flex items-center justify-center gap-2 text-white">
              {isScanning ? (
                <>
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                    <Loader size={18} />
                  </motion.div>
                  Starting Scan...
                </>
              ) : (
                <>
                  <Zap size={18} />
                  Start Scan
                </>
              )}
            </div>
          </motion.button>

          <motion.button
            className="px-6 py-3 glass rounded-lg text-muted-foreground hover:text-foreground font-semibold transition-colors"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => window.open('https://github.com', '_blank')}
          >
            Docs
          </motion.button>
        </div>

        <p className="text-xs text-muted-foreground text-center">
          Scans typically complete in 2–5 minutes depending on repository size
        </p>
      </div>
    </motion.div>
  );
};
