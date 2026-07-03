import React, { useState, useEffect } from 'react';
import { useLocation } from 'wouter';
import { motion } from 'framer-motion';
import { ScanInputCard } from '@/components/ScanInputCard';
import { scanApi, handleApiError } from '@/lib/api';
import { toast } from 'sonner';
import { Activity, GitBranch, TrendingUp, ArrowRight } from 'lucide-react';

interface RecentScan {
  id: number;
  status: string;
  created_at?: string;
  upstream_url?: string;
  fork_url?: string;
}

export default function Dashboard() {
  const [, navigate] = useLocation();
  const [recentScans, setRecentScans] = useState<RecentScan[]>([]);
  const [loadingScans, setLoadingScans] = useState(true);

  // Load recent scans from backend API
  useEffect(() => {
    const loadScans = async () => {
      try {
        const data = await scanApi.listScans();
        setRecentScans(data);
      } catch (e) {
        console.error('Failed to load scans', e);
      } finally {
        setLoadingScans(false);
      }
    };
    loadScans();
  }, []);

  const handleScanClick = (scanId: number) => {
    navigate(`/scans/${scanId}`);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'emerald';
      case 'failed':
        return 'rose';
      case 'running':
        return 'amber';
      default:
        return 'gray';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <motion.section
        className="container mx-auto px-4 py-12 md:py-16"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
      >
        <div className="mb-12">
          <motion.h1
            className="text-4xl md:text-5xl font-bold text-foreground mb-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            Advanced Software Architecture Platform
          </motion.h1>
          <motion.p
            className="text-lg text-muted-foreground max-w-2xl"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            Powered by multiple AI agents debating and resolving conflicts between your upstream repository and fork.
          </motion.p>
        </div>

        {/* Feature Pills */}
        <motion.div
          className="flex flex-wrap gap-3 mb-12"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {[
            { icon: <GitBranch size={16} />, label: 'Multi-Agent Architecture' },
            { icon: <TrendingUp size={16} />, label: 'AST Analysis' },
            { icon: <Activity size={16} />, label: 'Autonomous Merge Planning' },
          ].map((pill, index) => (
            <motion.div
              key={index}
              className="flex items-center gap-2 px-4 py-2 glass rounded-full text-sm text-muted-foreground hover:text-foreground transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {pill.icon}
              {pill.label}
            </motion.div>
          ))}
        </motion.div>
      </motion.section>

      {/* Main Dashboard Grid */}
      <section className="container mx-auto px-4 pb-16">
        <div className="grid grid-cols-1 gap-6 mb-8">
          <ScanInputCard />
        </div>

        {/* Recent Activity Section */}
        <motion.section
          className="mt-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <h2 className="text-xl font-bold text-foreground mb-4">Recent Scans</h2>
          
          {loadingScans ? (
            <div className="glass rounded-2xl p-8">
              <div className="flex justify-center py-12">
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity }}>
                  <Activity size={32} className="text-gray-600" />
                </motion.div>
              </div>
            </div>
          ) : recentScans.length === 0 ? (
            <div className="glass rounded-2xl p-8">
              <div className="flex flex-col items-center justify-center py-12">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <GitBranch size={48} className="text-gray-600 mb-4" />
                </motion.div>
                <p className="text-gray-400 text-center">
                  No scans yet. Start your first scan above!
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recentScans.map((scan, index) => (
                <motion.div
                  key={scan.id}
                  className="glass rounded-xl p-5 cursor-pointer group"
                  whileHover={{ y: -4, scale: 1.02 }}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => handleScanClick(scan.id)}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Scan ID</p>
                      <p className="text-lg font-bold text-foreground font-mono">{scan.id}</p>
                    </div>
                    <motion.div
                      className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                        scan.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : scan.status === 'failed'
                          ? 'bg-red-500/20 text-red-400'
                          : scan.status === 'running'
                          ? 'bg-amber-500/20 text-amber-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}
                      animate={
                        scan.status === 'running'
                          ? { opacity: [0.5, 1, 0.5] }
                          : {}
                      }
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      {scan.status.charAt(0).toUpperCase() + scan.status.slice(1)}
                    </motion.div>
                  </div>

                  {scan.created_at && (
                    <p className="text-xs text-muted-foreground mb-4">
                      {new Date(scan.created_at).toLocaleString()}
                    </p>
                  )}

                  <div className="flex items-center justify-between pt-4 border-t border-border group-hover:border-border transition-colors">
                    <span className="text-xs text-muted-foreground">View details</span>
                    <motion.div
                      animate={{ x: [0, 4, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    >
                      <ArrowRight size={16} className="text-indigo-400" />
                    </motion.div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.section>
      </section>
    </div>
  );
}
