import React, { useState, useEffect } from 'react';
import { policyApi } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

interface AffectedPolicy {
  policy_id: number;
  name: string;
  category: string;
  priority: string;
  similarity_score: number;
  reason: string;
  agent_referenced: boolean;
}

interface PolicyImpactData {
  available: boolean;
  message?: string;
  affected_policies: AffectedPolicy[];
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  business_impact: string;
  escalation_needed: boolean;
  policy_impact_score: number;
}

interface Props {
  debateId: number;
  debateStatus?: string;
}

const RISK_CONFIG = {
  CRITICAL: { color: 'bg-red-500/20 border-red-500/40 text-red-300', badge: 'bg-red-500/30 text-red-200', icon: '🚨', glow: 'shadow-[0_0_16px_rgba(239,68,68,0.2)]' },
  HIGH:     { color: 'bg-orange-500/20 border-orange-500/40 text-orange-300', badge: 'bg-orange-500/30 text-orange-200', icon: '⚠️', glow: 'shadow-[0_0_16px_rgba(249,115,22,0.2)]' },
  MEDIUM:   { color: 'bg-amber-500/20 border-amber-500/40 text-amber-300', badge: 'bg-amber-500/30 text-amber-200', icon: '🔔', glow: '' },
  LOW:      { color: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300', badge: 'bg-emerald-500/30 text-emerald-200', icon: '✅', glow: '' },
};

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: 'text-red-300',
  HIGH: 'text-orange-300',
  MEDIUM: 'text-amber-300',
  LOW: 'text-emerald-300',
};

export const PolicyImpactPanel: React.FC<Props> = ({ debateId, debateStatus }) => {
  const [data, setData] = useState<PolicyImpactData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchImpact = async () => {
      try {
        const result = await policyApi.getPolicyImpact(debateId);
        if (!cancelled) setData(result);
      } catch {
        // Non-fatal — no policies uploaded
        if (!cancelled) setData({ available: false, affected_policies: [], risk_level: 'LOW', business_impact: '', escalation_needed: false, policy_impact_score: 0 });
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchImpact();

    // Re-fetch when debate completes
    let interval: ReturnType<typeof setInterval> | null = null;
    if (debateStatus === 'in_progress') {
      interval = setInterval(fetchImpact, 8000);
    }

    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
    };
  }, [debateId, debateStatus]);

  if (loading) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4 animate-pulse">
        <div className="h-4 w-32 bg-white/10 rounded mb-3" />
        <div className="h-3 w-full bg-white/5 rounded mb-2" />
        <div className="h-3 w-3/4 bg-white/5 rounded" />
      </div>
    );
  }

  if (!data || !data.available) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-4 h-4 text-white/30" />
          <span className="text-sm font-semibold text-white/40">Policy Impact</span>
        </div>
        <p className="text-xs text-white/30">
          No enterprise policies uploaded.{' '}
          <a href="/governance" className="text-indigo-400 hover:underline">Upload policies</a>{' '}
          to enable policy-aware analysis.
        </p>
      </div>
    );
  }

  const riskCfg = RISK_CONFIG[data.risk_level] || RISK_CONFIG.LOW;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`rounded-2xl border ${riskCfg.color} ${riskCfg.glow} overflow-hidden`}
    >
      {/* Panel Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4" />
          <span className="text-sm font-bold">Policy Impact</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${riskCfg.badge}`}>
            {riskCfg.icon} {data.risk_level}
          </span>
          {data.escalation_needed && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/30 text-red-200 font-bold animate-pulse">
              ESCALATE
            </span>
          )}
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 opacity-50" /> : <ChevronDown className="w-4 h-4 opacity-50" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Summary Bar */}
            <div className="px-4 pb-3 border-b border-white/10">
              <div className="flex items-center justify-between text-xs text-white/50 mb-1">
                <span>Policy Impact Score</span>
                <span className="font-mono">{(data.policy_impact_score * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${data.policy_impact_score * 100}%` }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                  className={`h-full rounded-full ${
                    data.risk_level === 'CRITICAL' ? 'bg-red-400' :
                    data.risk_level === 'HIGH' ? 'bg-orange-400' :
                    data.risk_level === 'MEDIUM' ? 'bg-amber-400' : 'bg-emerald-400'
                  }`}
                />
              </div>
            </div>

            {/* Business Impact Text */}
            {data.business_impact && (
              <div className="px-4 py-3 border-b border-white/10">
                <p className="text-xs text-white/60 leading-relaxed">{data.business_impact}</p>
              </div>
            )}

            {/* Affected Policies List */}
            <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
              {data.affected_policies.length === 0 ? (
                <p className="text-xs text-white/30 text-center">No policies matched.</p>
              ) : (
                data.affected_policies.map((policy, idx) => (
                  <motion.div
                    key={policy.policy_id}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.06 }}
                    className="p-3 bg-black/20 rounded-xl border border-white/10"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div>
                        <span className="text-xs font-bold text-white">{policy.name}</span>
                        {policy.agent_referenced && (
                          <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-indigo-500/30 text-indigo-300">
                            AI Referenced
                          </span>
                        )}
                      </div>
                      <span className={`text-xs font-semibold shrink-0 ${PRIORITY_COLORS[policy.priority] || 'text-white/60'}`}>
                        {policy.priority}
                      </span>
                    </div>
                    <p className="text-xs text-white/50 mb-1">{policy.category}</p>
                    <p className="text-xs text-white/40 italic">{policy.reason}</p>
                    <div className="mt-2 flex items-center gap-1.5">
                      <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-400/60 rounded-full"
                          style={{ width: `${policy.similarity_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-white/30">
                        {(policy.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
