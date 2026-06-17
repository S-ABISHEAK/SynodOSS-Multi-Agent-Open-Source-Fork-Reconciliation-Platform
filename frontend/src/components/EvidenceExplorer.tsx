import React, { useState } from 'react';

interface EvidenceItem {
  source: string;
  description: string;
  line_start?: number;
  line_end?: number;
  commit?: string;
  symbol?: string;
  confidence?: number;
  strength?: number;
}

interface AgentMessage {
  agent: string;
  round: number;
  response?: Record<string, unknown>;
}

interface EvidenceExplorerProps {
  messages: AgentMessage[] | null;
}

const AGENT_COLORS: Record<string, string> = {
  advocate: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  defender: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
  architect: 'text-violet-400 bg-violet-500/10 border-violet-500/30',
  judge: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  impact_analyst: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
};

function StrengthBadge({ strength }: { strength: number }) {
  const pct = Math.round(strength * 100);
  const color = pct >= 80 ? 'text-emerald-400' : pct >= 50 ? 'text-amber-400' : 'text-red-400';
  return <span className={`text-[10px] font-bold ${color}`}>{pct}%</span>;
}

export default function EvidenceExplorer({ messages }: EvidenceExplorerProps) {
  const [filter, setFilter] = useState<string>('all');

  if (!messages || messages.length === 0) return null;

  // Collect all evidence items across all agents
  const allEvidence: Array<EvidenceItem & { agent: string; round: number }> = [];

  for (const msg of messages) {
    const response = msg.response as Record<string, unknown> | undefined;
    const evidenceList = Array.isArray(response?.evidence_provided)
      ? (response.evidence_provided as EvidenceItem[])
      : [];

    for (const ev of evidenceList) {
      allEvidence.push({ ...ev, agent: msg.agent, round: msg.round });
    }
  }

  const agentNames = ['all', ...Array.from(new Set(allEvidence.map(e => e.agent)))];
  const filtered = filter === 'all' ? allEvidence : allEvidence.filter(e => e.agent === filter);

  if (filtered.length === 0)
    return (
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5">
        <h3 className="text-xs font-black text-neutral-400 uppercase tracking-widest">Evidence Explorer</h3>
        <p className="text-sm text-neutral-600 mt-3">No evidence items found.</p>
      </div>
    );

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-xs font-black text-neutral-400 uppercase tracking-widest">Evidence Explorer</h3>
        <span className="text-[10px] text-neutral-500">{filtered.length} items</span>
      </div>

      {/* Agent filter tabs */}
      <div className="flex gap-1 flex-wrap">
        {agentNames.map(agent => (
          <button
            key={agent}
            onClick={() => setFilter(agent)}
            className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border transition-all ${
              filter === agent
                ? AGENT_COLORS[agent] || 'text-white bg-neutral-700 border-neutral-600'
                : 'text-neutral-500 bg-transparent border-neutral-700 hover:border-neutral-500'
            }`}
          >
            {agent}
          </button>
        ))}
      </div>

      {/* Evidence list */}
      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {filtered.map((ev, i) => {
          const agentColor = AGENT_COLORS[ev.agent] || 'text-neutral-400 bg-neutral-800/50 border-neutral-700';
          const strength = ev.strength ?? ev.confidence ?? 0;
          return (
            <div
              key={i}
              className="bg-neutral-950 border border-neutral-800 rounded-xl p-3 space-y-1.5"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border ${agentColor}`}>
                    {ev.agent}
                  </span>
                  <span className="text-[9px] text-neutral-600">Round {ev.round}</span>
                  <span className="text-[9px] text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded">
                    {ev.source}
                  </span>
                </div>
                <StrengthBadge strength={strength} />
              </div>

              <p className="text-xs text-neutral-300 leading-relaxed">{ev.description}</p>

              <div className="flex gap-3 flex-wrap text-[9px] text-neutral-600 font-mono">
                {ev.symbol && <span>symbol: <span className="text-emerald-400">{ev.symbol}</span></span>}
                {ev.line_start != null && (
                  <span>
                    lines:{' '}
                    <span className="text-amber-400">
                      {ev.line_start}{ev.line_end != null && ev.line_end !== ev.line_start ? `–${ev.line_end}` : ''}
                    </span>
                  </span>
                )}
                {ev.commit && <span>commit: <span className="text-blue-400">{ev.commit.slice(0, 8)}</span></span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
