import React from 'react';
import { motion } from 'framer-motion';
import { FileText, AlertCircle, Zap, ExternalLink } from 'lucide-react';
import { useLocation } from 'wouter';

export interface ReconciliationUnit {
  id: number;
  unit_id: number;
  file_path: string;
  conflict_type: string;
  severity: string;
  summary: string;
  complexity_score: number;
  impact_score: number;
  debate_id: number | null;
  debate_status: string | null;
}

interface Props {
  units: ReconciliationUnit[];
  onDebateClick: (unitId: number) => void;
  startingDebate: number | null;
}

const getSeverityColor = (severity: string) => {
  const s = severity.toLowerCase();
  switch (s) {
    case 'critical':
      return 'from-red-500/20 to-red-600/10 border-red-500/30';
    case 'high':
      return 'from-orange-500/20 to-orange-600/10 border-orange-500/30';
    case 'medium':
      return 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/30';
    case 'low':
      return 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30';
    default:
      return 'from-gray-500/20 to-gray-600/10 border-gray-500/30';
  }
};

const getSeverityBadgeColor = (severity: string) => {
  const s = severity.toLowerCase();
  switch (s) {
    case 'critical':
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'high':
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    case 'medium':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    case 'low':
      return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  }
};

export const ConflictVisualization: React.FC<Props> = ({ units, onDebateClick, startingDebate }) => {
  const [, navigate] = useLocation();
  
  if (!units || units.length === 0) {
    return (
      <motion.div
        className="glass rounded-2xl p-6 col-span-1 lg:col-span-2 flex items-center justify-center min-h-[300px]"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      >
        <div className="text-center text-white/50">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>No conflicts detected in this scan.</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="glass rounded-2xl p-6 col-span-1 lg:col-span-2"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.15 }}
    >
      <h3 className="text-lg font-bold text-white mb-4">Conflict Overview</h3>

      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
        {units.map((unit, index) => (
          <motion.div
            key={unit.id}
            className={`border glass rounded-xl p-4 group transition-all ${getSeverityColor(unit.severity)}`}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <div className="flex items-start gap-4">
              {/* File Icon */}
              <div className="p-2 rounded-lg bg-white/5 group-hover:bg-white/10 transition-colors">
                <FileText size={18} className="text-indigo-400" />
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <p className="text-sm font-semibold text-white truncate">{unit.file_path}</p>
                  <span className="text-xs px-2 py-1 rounded bg-white/10 text-gray-400">
                    {unit.conflict_type}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mb-3">{unit.summary}</p>

                {/* Complexity & Impact Bars */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-white/40 w-16">Complexity</span>
                    <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-indigo-500 to-cyan-500"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, (unit.complexity_score / 100) * 100)}%` }}
                        transition={{ duration: 0.8, delay: index * 0.1 + 0.2 }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-8 text-right">{Math.round(unit.complexity_score)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-white/40 w-16">Impact</span>
                    <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-orange-500 to-red-500"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, (unit.impact_score / 100) * 100)}%` }}
                        transition={{ duration: 0.8, delay: index * 0.1 + 0.3 }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-8 text-right">{Math.round(unit.impact_score)}</span>
                  </div>
                </div>
              </div>

              {/* Severity Badge & Actions */}
              <div className="flex flex-col items-end gap-2">
                <motion.div
                  className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getSeverityBadgeColor(unit.severity)}`}
                  whileHover={{ scale: 1.05 }}
                >
                  {unit.severity.toUpperCase()}
                </motion.div>

                {unit.debate_id ? (
                  <motion.button
                    onClick={() => navigate(`/debates/${unit.debate_id}`)}
                    className="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30 transition-colors flex items-center gap-1"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <ExternalLink size={12} />
                    View Debate
                  </motion.button>
                ) : (
                  <motion.button
                    onClick={() => onDebateClick(unit.unit_id)}
                    disabled={startingDebate === unit.unit_id || !unit.unit_id}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors
                      ${(!unit.unit_id || startingDebate === unit.unit_id) 
                        ? 'bg-gray-500/20 text-gray-500 border-gray-500/30 cursor-not-allowed' 
                        : 'bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30 border-indigo-500/30'
                      } border`}
                    whileHover={{ scale: (!unit.unit_id || startingDebate === unit.unit_id) ? 1 : 1.05 }}
                    whileTap={{ scale: (!unit.unit_id || startingDebate === unit.unit_id) ? 1 : 0.95 }}
                  >
                    <Zap size={12} />
                    {startingDebate === unit.unit_id ? 'Starting...' : 'Debate'}
                  </motion.button>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Summary */}
      <motion.div
        className="mt-4 pt-4 border-t border-white/10 grid grid-cols-3 gap-3"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Total Conflicts</p>
          <p className="text-lg font-bold text-white">{units.length}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Avg Complexity</p>
          <p className="text-lg font-bold text-white">
            {units.length > 0 ? Math.round(units.reduce((a, c) => a + c.complexity_score, 0) / units.length) : 0}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Critical</p>
          <p className="text-lg font-bold text-red-400">
            {units.filter((c) => c.severity.toLowerCase() === 'critical').length}
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
};
