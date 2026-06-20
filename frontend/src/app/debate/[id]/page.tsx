'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import axios from 'axios';
import InteractiveDiffViewer from '@/components/InteractiveDiffViewer';
import ConflictImpactCard from '@/components/ConflictImpactCard';
import VerificationDashboard from '@/components/VerificationDashboard';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const AGENT_CONFIG: Record<string, { color: string; label: string; bg: string; border: string }> = {
  advocate: { color: 'text-emerald-400', label: 'Advocate', bg: 'bg-emerald-500', border: 'border-emerald-500/30' },
  defender: { color: 'text-rose-400',   label: 'Defender', bg: 'bg-rose-500',    border: 'border-rose-500/30' },
  architect: { color: 'text-indigo-400', label: 'Architect', bg: 'bg-indigo-500', border: 'border-indigo-500/30' },
  judge:     { color: 'text-blue-400',   label: 'Judge',     bg: 'bg-blue-500',   border: 'border-blue-500/30' },
};

const RESOLUTION_STYLES: Record<string, { bg: string; text: string; border: string; icon: string }> = {
  ACCEPT_UPSTREAM:   { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/50', icon: '✓' },
  REJECT_UPSTREAM:   { bg: 'bg-rose-500/20',    text: 'text-rose-400',    border: 'border-rose-500/50',    icon: '✕' },
  MERGE_PARTIAL:     { bg: 'bg-amber-500/20',   text: 'text-amber-400',   border: 'border-amber-500/50',   icon: '✂' },
  REFACTOR_ADAPTER:  { bg: 'bg-indigo-500/20',  text: 'text-indigo-400',  border: 'border-indigo-500/50',  icon: '⚡' },
  ESCALATE_HUMAN:    { bg: 'bg-red-500/20',     text: 'text-red-500',     border: 'border-red-500/50',     icon: '⚠' },
};

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'escalated']);

export default function DebateWorkspace() {
  const params = useParams();
  const debateId = Number(params.id);

  const [debate, setDebate] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const failCountRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const transcriptContainerRef = useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = useState(false);

  const isNearBottom = () => {
    const el = transcriptContainerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 150;
  };

  const handleScroll = () => setUserScrolled(!isNearBottom());

  const jumpToLatest = () => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setUserScrolled(false);
  };

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const fetchDebate = async () => {
    if (!debateId) return;
    try {
      const [dRes, mRes] = await Promise.all([
        axios.get(`${API_URL}/debates/${debateId}`),
        axios.get(`${API_URL}/debates/${debateId}/rounds`),
      ]);
      const data = dRes.data;
      setDebate(data);
      setMessages(mRes.data ?? []);
      setFetchError(null);
      failCountRef.current = 0;
      setIsInitialLoad(false);
      // Stop polling once debate is in a terminal state
      if (data?.status && TERMINAL_STATUSES.has(data.status)) {
        stopPolling();
      }
    } catch (e: any) {
      failCountRef.current += 1;
      console.error('Debate fetch error:', e);
      if (failCountRef.current >= 3) {
        setFetchError(
          e?.response?.status === 404
            ? `Debate #${debateId} not found. It may have been deleted.`
            : `Unable to reach the backend. Is uvicorn running on port 8000?`
        );
        stopPolling();
        setIsInitialLoad(false);
      }
    }
  };

  useEffect(() => {
    if (!debateId) return;
    fetchDebate();
    intervalRef.current = setInterval(fetchDebate, 3000);
    return () => stopPolling();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debateId]);

  // Auto-scroll when new messages arrive (unless user scrolled up)
  useEffect(() => {
    if (!userScrolled) {
      transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // ── Loading / Error Gate ────────────────────────────────────────────
  if (isInitialLoad && !debate && !fetchError) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-6 p-8">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-indigo-500/20 rounded-full" />
            <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin absolute inset-0" />
          </div>
          <div className="text-center">
            <p className="text-indigo-400 font-mono font-bold animate-pulse">Initializing Council Workspace...</p>
            <p className="text-neutral-600 text-xs mt-2 font-mono">Debate #{debateId} · Connecting to API</p>
          </div>
        </div>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center p-8">
        <div className="max-w-md text-center space-y-6">
          <div className="w-16 h-16 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center justify-center mx-auto text-3xl">⚠</div>
          <div>
            <h2 className="text-xl font-black text-red-400 mb-2">Council Unreachable</h2>
            <p className="text-neutral-400 text-sm leading-relaxed">{fetchError}</p>
          </div>
          <button
            onClick={() => {
              setFetchError(null);
              setIsInitialLoad(true);
              failCountRef.current = 0;
              intervalRef.current = setInterval(fetchDebate, 3000);
              fetchDebate();
            }}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl transition-colors text-sm"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const isCompleted = debate.status === 'completed';
  const isFailed = debate.status === 'failed';
  const isEscalated = debate.status === 'escalated';

  const getStatusBadge = () => {
    if (isCompleted) return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    if (isEscalated) return 'text-red-400 bg-red-400/10 border-red-400/20';
    if (isFailed) return 'text-rose-400 bg-rose-400/10 border-rose-400/20';
    return 'text-amber-400 bg-amber-400/10 border-amber-400/20 animate-pulse';
  };

  const getStatusLabel = () => {
    if (isCompleted) return 'Consensus Reached';
    if (isEscalated) return 'Escalated to Human';
    if (isFailed) return 'Failed';
    return 'Agents Deliberating...';
  };

  const safeParseMessage = (raw: string) => {
    try {
      if (typeof raw === 'object') return raw;
      return JSON.parse(raw);
    } catch {
      return { analysis: raw };
    }
  };

  const resolutionAction: string | undefined = debate.resolution_action;
  const resBadge = resolutionAction ? RESOLUTION_STYLES[resolutionAction] : null;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-4 md:p-8 font-sans selection:bg-indigo-500/30">
      <main className="max-w-5xl mx-auto space-y-6 mt-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-neutral-900/50 p-6 rounded-2xl border border-neutral-800 backdrop-blur-xl">
          <div>
            <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-white to-neutral-400 bg-clip-text text-transparent">
              Multi-Agent Reasoning Council
            </h1>
            <p className="text-neutral-400 mt-1 font-mono text-sm">Debate #{debate.id}</p>
          </div>
          <div className="flex items-center gap-3">
            {resBadge && (
              <span
                id="resolution-action-badge"
                className={`px-3 py-1.5 rounded-full border text-xs font-black uppercase tracking-widest ${resBadge.bg} ${resBadge.text} ${resBadge.border}`}
              >
                {resBadge.icon} {resolutionAction?.replace('_', ' ')}
              </span>
            )}
            <span className={`px-4 py-1.5 rounded-full border text-sm font-bold uppercase tracking-widest ${getStatusBadge()}`}>
              {getStatusLabel()}
            </span>
          </div>
        </header>

        {/* ── Escalation Banner ───────────────────────────────────────────── */}
        {isEscalated && (
          <div className="bg-red-950/40 border border-red-700/50 rounded-2xl p-5 flex items-start gap-4">
            <span className="text-red-400 text-2xl mt-0.5">⚠</span>
            <div>
              <p className="text-red-300 font-bold text-sm uppercase tracking-widest mb-1">Human Review Required</p>
              <p className="text-red-200/70 text-sm leading-relaxed">
                The council's confidence fell below the 65% threshold. This conflict is too complex or ambiguous
                for automated resolution and has been escalated for manual review.
              </p>
            </div>
          </div>
        )}

        {/* ── Diff Viewer ─────────────────────────────────────────────────── */}
        {debate.diff_hunk && (
          <InteractiveDiffViewer diffHunk={debate.diff_hunk} filePath={debate.file_path ?? 'Unknown'} />
        )}

        {/* ── Architecture & Verification Dashboards ──────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ConflictImpactCard unit={debate} />
          <VerificationDashboard debate={debate} messages={messages} />
        </div>

        {/* ── Metrics Grid ────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Confidence Score',   value: debate.confidence        != null ? `${(debate.confidence * 100).toFixed(1)}%`        : '--', color: 'text-indigo-400' },
            { label: 'Verification Score', value: debate.verification_score != null ? `${(debate.verification_score * 100).toFixed(1)}%` : '--', color: 'text-blue-400'   },
            { label: 'Evidence Count',     value: debate.evidence_count ?? 0,                                                                    color: 'text-emerald-400' },
            { label: 'Token Usage',        value: debate.token_usage ?? 0,                                                                       color: 'text-white'       },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-neutral-900 p-5 rounded-2xl border border-neutral-800 flex flex-col items-center text-center shadow-lg hover:border-neutral-700 transition-colors">
              <div className="text-[10px] font-black text-neutral-500 uppercase tracking-widest mb-2">{label}</div>
              <div className={`text-3xl font-black ${color}`}>{value}</div>
            </div>
          ))}
        </div>

        {/* ── Architectural Proposal ───────────────────────────────────────── */}
        {debate.architectural_proposal && (
          <section className="bg-gradient-to-br from-indigo-900/40 to-neutral-900 border border-indigo-500/30 p-8 rounded-2xl shadow-2xl shadow-indigo-900/20">
            <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Architectural Proposal
            </h3>
            <p className="text-lg text-indigo-50 leading-relaxed font-medium whitespace-pre-wrap">
              {debate.architectural_proposal}
            </p>
          </section>
        )}

        {/* ── Debate Transcript ────────────────────────────────────────────── */}
        <section className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden shadow-2xl shadow-black/50">
          <div className="p-5 border-b border-neutral-800 bg-neutral-950/50 flex justify-between items-center">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <svg className="w-5 h-5 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              Architecture Decision Log
            </h3>
            <span className="text-xs text-neutral-500 font-mono bg-neutral-900 px-3 py-1 rounded-full border border-neutral-800">
              {messages.length} messages
            </span>
          </div>

          <div
            ref={transcriptContainerRef}
            onScroll={handleScroll}
            className="relative p-6 space-y-6 max-h-[800px] overflow-y-auto scroll-smooth"
          >
            {/* Jump to latest button — shown when user has scrolled up */}
            {userScrolled && (
              <div className="sticky top-2 z-10 flex justify-center pointer-events-none">
                <button
                  onClick={jumpToLatest}
                  className="pointer-events-auto flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-900/40 transition-all animate-bounce"
                >
                  <span>Jump to Latest</span>
                  <span>↓</span>
                </button>
              </div>
            )}
            {messages.length === 0 ? (
              <div className="text-center text-neutral-500 font-mono py-16 flex flex-col items-center gap-4">
                <div className="w-8 h-8 border-2 border-neutral-700 border-t-neutral-400 rounded-full animate-spin" />
                <span>Agents are deliberating...</span>
              </div>
            ) : (
              messages.map((msg, idx) => {
                const content = safeParseMessage(msg.message);
                const rawAgent = msg.agent as string;
                const isRebuttal = rawAgent.endsWith('_rebuttal') || rawAgent.includes('_rebuttal');
                const agent = rawAgent.replace('_rebuttal', '');
                
                const cfg = AGENT_CONFIG[agent] ?? { color: 'text-neutral-300', label: agent, bg: 'bg-neutral-700', border: 'border-neutral-700' };
                const evidenceRefs: any[] = Array.isArray(msg.evidence_refs) ? msg.evidence_refs : [];

                const roundLabels: Record<number, string> = {
                  1: "Round 1: Independent Analysis",
                  2: "Round 2: Cross-Examination",
                  3: "Round 3: Architect Synthesis",
                  4: "Round 4: Verification"
                };

                const isFirstOfRound = idx === 0 || messages[idx - 1].round !== msg.round;

                return (
                  <div key={idx} className="space-y-6">
                    {isFirstOfRound && (
                      <div className="flex items-center gap-4 py-2">
                        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-neutral-700 to-transparent"></div>
                        <span className="text-[10px] font-black text-neutral-500 uppercase tracking-widest">{roundLabels[msg.round] || `Round ${msg.round}`}</span>
                        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-neutral-700 to-transparent"></div>
                      </div>
                    )}

                    <div className={`bg-neutral-950/60 border ${cfg.border} rounded-2xl p-6 shadow-sm`}>
                      <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-full ${cfg.bg} flex items-center justify-center text-white text-sm font-black shadow-md`}>
                            {agent.charAt(0).toUpperCase()}
                          </div>
                          <span className={`font-bold uppercase tracking-wider text-sm ${cfg.color}`}>
                            {cfg.label} {isRebuttal && <span className="text-neutral-500 text-[10px] ml-2 border border-neutral-700 px-2 py-0.5 rounded-full bg-neutral-900">Rebuttal</span>}
                          </span>
                        </div>
                        {agent === 'architect' && content.resolution_action && (
                          <span className="text-[10px] font-black text-white bg-indigo-500/20 border border-indigo-500/50 px-3 py-1 rounded-full shadow-lg shadow-indigo-500/20">
                            {content.resolution_action}
                          </span>
                        )}
                      </div>

                      <div className="text-neutral-300 leading-relaxed text-[15px] pl-12 space-y-4">
                        {agent === 'judge' ? (
                          <div className="space-y-3">
                            <p>{content.verification_summary ?? content.analysis ?? '—'}</p>
                            {content.invalidated_claims?.length > 0 && (
                              <div className="bg-rose-950/30 border border-rose-900/50 p-3 rounded-lg text-sm text-rose-300">
                                <span className="font-bold text-rose-400 block mb-1">Invalidated Claims:</span>
                                <ul className="list-disc pl-5 space-y-1">
                                  {content.invalidated_claims.map((claim: string, i: number) => <li key={i}>{claim}</li>)}
                                </ul>
                              </div>
                            )}
                            {content.adjusted_confidence_penalty != null && (
                              <div className="inline-flex items-center gap-2 mt-2 px-3 py-1.5 bg-rose-950/40 border border-rose-900/50 rounded-lg text-sm">
                                <span className="text-rose-400 font-bold text-[10px] uppercase tracking-wider">Confidence Penalty</span>
                                <span className="text-rose-300 font-mono text-xs">−{(content.adjusted_confidence_penalty * 100).toFixed(0)}%</span>
                              </div>
                            )}
                          </div>
                        ) : isRebuttal ? (
                          <div className="space-y-3">
                            <p>{content.rebuttal}</p>
                            {content.conceded_points?.length > 0 && (
                              <div className="bg-emerald-950/20 border border-emerald-900/40 p-3 rounded-lg text-sm text-emerald-300/80 mt-3">
                                <span className="font-bold text-emerald-500/80 block mb-1">Conceded Points:</span>
                                <ul className="list-disc pl-5 space-y-1">
                                  {content.conceded_points.map((p: string, i: number) => <li key={i}>{p}</li>)}
                                </ul>
                              </div>
                            )}
                            {content.contested_points?.length > 0 && (
                              <div className="bg-amber-950/20 border border-amber-900/40 p-3 rounded-lg text-sm text-amber-300/80 mt-3">
                                <span className="font-bold text-amber-500/80 block mb-1">Contested Points:</span>
                                <ul className="list-disc pl-5 space-y-1">
                                  {content.contested_points.map((p: string, i: number) => <li key={i}>{p}</li>)}
                                </ul>
                              </div>
                            )}
                          </div>
                        ) : (
                          <p>{content.analysis ?? content.rationale ?? content.content ?? '—'}</p>
                        )}

                        {content.implementation_steps && content.implementation_steps.length > 0 && (
                           <div className="bg-neutral-900 border border-neutral-800 p-4 rounded-lg mt-4">
                             <h4 className="text-[10px] font-black text-neutral-400 uppercase tracking-widest mb-2">Implementation Steps</h4>
                             <ol className="list-decimal pl-5 space-y-1 text-sm text-neutral-300">
                               {content.implementation_steps.map((step: string, i: number) => <li key={i}>{step}</li>)}
                             </ol>
                           </div>
                        )}

                        {evidenceRefs.length > 0 && (
                          <div className="mt-5 pt-5 border-t border-neutral-800/50">
                            <p className="text-[10px] font-black text-neutral-600 uppercase tracking-widest mb-3">Evidence Cited</p>
                            <ul className="space-y-2">
                              {evidenceRefs.map((ev: any, i: number) => (
                                <li key={i} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-l-2 border-emerald-500/60 pl-3 bg-neutral-900/50 py-2 pr-3 rounded-r-lg text-sm">
                                  <div className="flex flex-col gap-1 w-full sm:w-auto">
                                    <span className="text-neutral-300">{ev.description ?? String(ev)}</span>
                                    <span className="text-[10px] text-neutral-500 font-mono">Source: {ev.source ?? 'unknown'}</span>
                                  </div>
                                  <div className="flex items-center gap-2 mt-1 sm:mt-0">
                                    {ev.line_start && (
                                      <span className="text-indigo-300 font-mono text-[10px] bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/30 whitespace-nowrap">
                                        L{ev.line_start}{ev.line_end && ev.line_end !== ev.line_start ? `–${ev.line_end}` : ''}
                                      </span>
                                    )}
                                    {ev.strength != null && (
                                      <span className="text-emerald-400 font-mono text-[10px] bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 whitespace-nowrap">
                                        Strength: {Number(ev.strength).toFixed(2)}
                                      </span>
                                    )}
                                  </div>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}

            {!isCompleted && !isEscalated && !isFailed && (
              <div className="text-center py-8">
                <span className="inline-block w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-xs text-indigo-400 mt-3 uppercase tracking-widest font-bold animate-pulse">
                  Council in Session
                </p>
              </div>
            )}
            <div ref={transcriptEndRef} />
          </div>
        </section>

      </main>
    </div>
  );
}
