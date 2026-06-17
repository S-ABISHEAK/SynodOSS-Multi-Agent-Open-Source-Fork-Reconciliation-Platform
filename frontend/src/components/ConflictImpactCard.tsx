import React from 'react';

interface UnitProps {
  unit: Record<string, unknown> | null;
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(Math.max(score, 0), 100);
  const color =
    pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-orange-500' : pct >= 30 ? 'bg-amber-400' : 'bg-emerald-500';
  return (
    <div className="w-full bg-neutral-800 rounded-full h-1.5 mt-1">
      <div className={`h-1.5 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function ConflictImpactCard({ unit }: UnitProps) {
  if (!unit) return null;

  const impactScore = typeof unit.impact_score === 'number' ? unit.impact_score : 0;
  const affectedFunctions = Array.isArray(unit.affected_functions) ? unit.affected_functions : [];
  const affectedModules = Array.isArray(unit.affected_modules) ? unit.affected_modules : [];
  const criticalPaths = Array.isArray(unit.critical_paths) ? unit.critical_paths : [];
  const depDepth = typeof unit.dependency_depth === 'number' ? unit.dependency_depth : 0;

  const riskLabel =
    impactScore >= 90 ? 'CRITICAL' : impactScore >= 70 ? 'HIGH' : impactScore >= 30 ? 'MEDIUM' : 'LOW';
  const riskColor =
    impactScore >= 90
      ? 'text-red-400 bg-red-500/10'
      : impactScore >= 70
      ? 'text-orange-400 bg-orange-500/10'
      : impactScore >= 30
      ? 'text-amber-400 bg-amber-500/10'
      : 'text-emerald-400 bg-emerald-500/10';

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5 shadow-lg space-y-4">
      <h3 className="text-xs font-black text-neutral-400 uppercase tracking-widest">Architectural Impact</h3>

      {/* Symbol + Layer */}
      <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
        <span className="text-sm text-neutral-500">Layer</span>
        <span className="text-sm font-bold text-indigo-400">{String(unit.architectural_layer || 'Unknown')}</span>
      </div>
      <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
        <span className="text-sm text-neutral-500">Symbol</span>
        <span className="text-sm font-mono text-emerald-400">{String(unit.symbol || 'Unknown')}</span>
      </div>
      <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
        <span className="text-sm text-neutral-500">Type</span>
        <span className="text-xs font-bold text-amber-400 uppercase bg-amber-500/10 px-2 py-0.5 rounded-full">
          {String(unit.symbol_type || 'Unknown')}
        </span>
      </div>

      {/* Impact Score */}
      <div className="border-b border-neutral-800 pb-3">
        <div className="flex justify-between items-center">
          <span className="text-sm text-neutral-500">Impact Score</span>
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${riskColor}`}>
              {riskLabel}
            </span>
            <span className="text-sm font-bold text-white">{impactScore.toFixed(1)}</span>
          </div>
        </div>
        <ScoreBar score={impactScore} />
      </div>

      {/* Blast Radius */}
      <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
        <span className="text-sm text-neutral-500">Affected Functions</span>
        <span className="text-sm font-bold text-white">{affectedFunctions.length}</span>
      </div>
      <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
        <span className="text-sm text-neutral-500">Affected Modules</span>
        <span className="text-sm font-bold text-white">{affectedModules.length}</span>
      </div>
      <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
        <span className="text-sm text-neutral-500">Dependency Depth</span>
        <span className="text-sm font-bold text-purple-400">{depDepth}</span>
      </div>

      {/* Critical Paths */}
      {criticalPaths.length > 0 && (
        <div>
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">Critical Paths</p>
          <div className="space-y-1">
            {(criticalPaths as string[][]).slice(0, 3).map((path, i) => (
              <p key={i} className="text-[10px] font-mono text-neutral-400 truncate">
                {path.join(' → ')}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
