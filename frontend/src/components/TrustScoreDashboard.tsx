import React from 'react';

interface TrustScoreProps {
  debate: Record<string, unknown> | null;
}

function Ring({ value, label, color }: { value: number; label: string; color: string }) {
  const pct = Math.min(Math.max(value * 100, 0), 100);
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={radius} fill="none" stroke="#262626" strokeWidth="6" />
        <circle
          cx="36" cy="36" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform="rotate(-90 36 36)"
          style={{ transition: 'stroke-dashoffset 0.5s ease' }}
        />
        <text x="36" y="40" textAnchor="middle" fill="white" fontSize="11" fontWeight="bold">
          {pct.toFixed(0)}%
        </text>
      </svg>
      <span className="text-[10px] text-neutral-500 text-center leading-tight">{label}</span>
    </div>
  );
}

export default function TrustScoreDashboard({ debate }: TrustScoreProps) {
  if (!debate) return null;

  const judgeMsg = Array.isArray(debate.messages)
    ? (debate.messages as Record<string, unknown>[]).find(m => m.agent === 'judge')
    : null;

  const response = judgeMsg?.response as Record<string, unknown> | undefined;

  const trustScore = typeof response?.trust_score === 'number' ? response.trust_score : 0;
  const evidenceValidity = typeof response?.evidence_validity_score === 'number' ? response.evidence_validity_score : 0;
  const graphConsistency = typeof response?.graph_consistency_score === 'number' ? response.graph_consistency_score : 0;
  const agentAgreement = typeof response?.agent_agreement_score === 'number' ? response.agent_agreement_score : 0;
  const confidencePenalty = typeof response?.adjusted_confidence_penalty === 'number' ? response.adjusted_confidence_penalty : 0;

  const trustColor =
    trustScore >= 0.8 ? '#22c55e' : trustScore >= 0.6 ? '#f59e0b' : trustScore >= 0.4 ? '#f97316' : '#ef4444';

  const trustLabel =
    trustScore >= 0.8 ? 'HIGH TRUST' : trustScore >= 0.6 ? 'MODERATE' : trustScore >= 0.4 ? 'LOW TRUST' : 'UNTRUSTED';
  const trustLabelColor =
    trustScore >= 0.8
      ? 'text-emerald-400 bg-emerald-500/10'
      : trustScore >= 0.6
      ? 'text-amber-400 bg-amber-500/10'
      : trustScore >= 0.4
      ? 'text-orange-400 bg-orange-500/10'
      : 'text-red-400 bg-red-500/10';

  const invalidatedClaims = Array.isArray(response?.invalidated_claims) ? response.invalidated_claims as string[] : [];

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5 shadow-lg space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-black text-neutral-400 uppercase tracking-widest">Trust Score</h3>
        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${trustLabelColor}`}>
          {trustLabel}
        </span>
      </div>

      {/* Main trust score ring */}
      <div className="flex justify-center">
        <Ring value={trustScore} label="Overall Trust" color={trustColor} />
      </div>

      {/* Sub-scores */}
      <div className="grid grid-cols-4 gap-2">
        <Ring value={evidenceValidity} label="Evidence Validity" color="#818cf8" />
        <Ring value={graphConsistency} label="Graph Consistency" color="#34d399" />
        <Ring value={agentAgreement} label="Agent Agreement" color="#f59e0b" />
        <Ring value={1 - confidencePenalty} label="Confidence" color="#a78bfa" />
      </div>

      {/* Formula breakdown */}
      <div className="bg-neutral-950 rounded-xl p-3 text-[10px] font-mono text-neutral-500 space-y-0.5">
        <p className="text-neutral-300 font-bold mb-1">Trust = EV×0.40 + GC×0.35 + AA×0.15 + CF×0.10</p>
        <p>Evidence Validity  (EV): {(evidenceValidity * 100).toFixed(0)}%</p>
        <p>Graph Consistency  (GC): {(graphConsistency * 100).toFixed(0)}%</p>
        <p>Agent Agreement    (AA): {(agentAgreement * 100).toFixed(0)}%</p>
        <p>Confidence Factor  (CF): {((1 - confidencePenalty) * 100).toFixed(0)}%</p>
      </div>

      {/* Invalidated claims */}
      {invalidatedClaims.length > 0 && (
        <div>
          <p className="text-xs font-bold text-red-400 uppercase tracking-widest mb-2">
            Invalidated Claims ({invalidatedClaims.length})
          </p>
          <ul className="space-y-1">
            {invalidatedClaims.slice(0, 5).map((claim, i) => (
              <li key={i} className="text-[10px] text-neutral-400 bg-red-500/5 border border-red-500/20 rounded px-2 py-1 truncate">
                {claim}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
