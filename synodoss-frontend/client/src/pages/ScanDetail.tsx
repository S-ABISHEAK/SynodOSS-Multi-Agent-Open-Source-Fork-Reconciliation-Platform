import React, { useState, useEffect } from 'react';
import { useLocation, useParams } from 'wouter';
import { motion } from 'framer-motion';
import { ConflictVisualization } from '@/components/ConflictVisualization';
import { scanApi, debateApi, handleApiError } from '@/lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Database, AlertCircle } from 'lucide-react';

interface ReconciliationUnit {
  id: number;
  file_path: string;
  conflict_type: string;
  severity: string;
  complexity_score: number;
  impact_score: number;
}

interface ScanMetrics {
  commit_gap?: number;
  added_files?: number;
  deleted_files?: number;
  modified_files?: number;
}

export default function ScanDetail() {
  const [, navigate] = useLocation();
  const { id: scanId } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [units, setUnits] = useState<ReconciliationUnit[]>([]);
  const [metrics, setMetrics] = useState<ScanMetrics | null>(null);
  const [scanStatus, setScanStatus] = useState<string>('pending');
  const [startingDebate, setStartingDebate] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      if (!scanId) return;

      try {
        const scanIdNum = parseInt(scanId);

        // Load scan status
        const statusData = await scanApi.getScanStatus(scanIdNum);
        if (!cancelled) setScanStatus(statusData.status);

        // Load summary/metrics
        const metricsData = await scanApi.getScanSummary(scanIdNum);
        if (!cancelled) setMetrics(metricsData);

        // Load conflicts (mapped to units)
        const conflictsData = await scanApi.getConflicts(scanIdNum);
        if (!cancelled) setUnits(conflictsData);
      } catch (error) {
        if (!cancelled) {
          const message = handleApiError(error);
          toast.error(message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadData();

    // Poll every 3 s while scan is still running
    const interval = setInterval(loadData, 3000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [scanId]);

  const handleStartDebate = async (unitId: number) => {
    setStartingDebate(unitId);
    try {
      const result = await debateApi.startDebate(unitId);
      const debateId = result.debate_id;
      toast.success(`Debate started! ID: ${debateId}`);
      navigate(`/debates/${debateId}`);
    } catch (error) {
      const message = handleApiError(error);
      toast.error(message);
    } finally {
      setStartingDebate(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity }}>
          <AlertCircle size={32} className="text-gray-600" />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <motion.section
        className="container mx-auto px-4 py-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {/* Back Button */}
        <motion.button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-6"
          whileHover={{ x: -4 }}
        >
          <ArrowLeft size={18} />
          Back to Dashboard
        </motion.button>

        {/* Title Section */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <motion.h1
              className="text-3xl md:text-4xl font-bold text-white mb-2"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              Scan Analysis
            </motion.h1>
            <motion.p
              className="text-gray-400"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              Scan ID: <span className="font-mono text-indigo-400">{scanId}</span>
            </motion.p>
          </div>

          <div className="flex items-center gap-4">
            <motion.button
              onClick={() => navigate(`/scans/${scanId}/graph`)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-lg hover:bg-indigo-500/30 transition-colors"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
            >
              <Database size={16} />
              <span className="text-sm font-semibold">View Knowledge Graph</span>
            </motion.button>

            {/* Status Badge */}
            <motion.div
            className={`flex items-center gap-2 px-4 py-2 glass rounded-lg ${
              scanStatus === 'completed'
                ? 'bg-emerald-500/10 border-emerald-500/30'
                : scanStatus === 'failed'
                ? 'bg-red-500/10 border-red-500/30'
                : 'bg-amber-500/10 border-amber-500/30'
            } border`}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            <motion.div
              className={`w-2 h-2 rounded-full ${
                scanStatus === 'completed'
                  ? 'bg-emerald-500'
                  : scanStatus === 'failed'
                  ? 'bg-red-500'
                  : 'bg-amber-500'
              }`}
              animate={{ scale: [1, 1.5, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span
              className={`text-sm font-semibold ${
                scanStatus === 'completed'
                  ? 'text-emerald-400'
                  : scanStatus === 'failed'
                  ? 'text-red-400'
                  : 'text-amber-400'
              }`}
            >
              {scanStatus.charAt(0).toUpperCase() + scanStatus.slice(1)}
            </span>
            </motion.div>
          </div>
        </div>
      </motion.section>

      {/* Main Content Grid */}
      <section className="container mx-auto px-4 pb-16">
        {/* Real Conflicts from backend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <ConflictVisualization
            units={units}
            onDebateClick={handleStartDebate}
            startingDebate={startingDebate}
          />
        </motion.div>
      </section>
    </div>
  );
}
