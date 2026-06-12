'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import axios from 'axios';
import InteractiveDiffViewer from '@/components/InteractiveDiffViewer';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Round Labels (Layer 6) ────────────────────────────────────────────────────
const ROUND_LABELS: Record<number, { label: string; description: string; color: string }> = {
  1: { label: 'Round 1 — Initial Analysis',      description: 'Independent first-pass analysis by each agent.',            color: 'from-neutral-700/60 to-neutral-800/30' },
  2: { label: 'Round 2 — Cross-Examination',     description: 'Each agent rebuts the other\'s opening argument.',           color: 'from-amber-900/30 to-neutral-800/30' },
  3: { label: 'Round 3 — Architect Synthesis',   description: 'Architect reads all arguments and issues a final verdict.',  color: 'from-indigo-900/30 to-neutral-800/30' },
  4: { label: 'Round 4 — Verification',          description: 'Judge audits all evidence and applies confidence penalty.',  color: 'from-blue-900/30 to-neutral-800/30' },
};

// ── Resolution Action Badge Styles (Layer 6) ──────────────────────────────────
const RESOLUTION_STYLES: Record<string, { bg: string; text: string; border: string; icon: string }> = {
  ACCEPT_UPSTREAM:  { bg: 'bg-emerald-500/15', text: 'text-emerald-300', border: 'border-emerald-500/40', icon: '↑' },
  REJECT_UPSTREAM:  { bg: 'bg-rose-500/15',    text: 'text-rose-300',    border: 'border-rose-500/40',    icon: '✕' },
  MERGE_PARTIAL:    { bg: 'bg-amber-500/15',   text: 'text-amber-300',   border: 'border-amber-500/40',   icon: '⊕' },
  REFACTOR_ADAPTER: { bg: 'bg-indigo-500/15',  text: 'text-indigo-300',  border: 'border-indigo-500/40',  icon: '⟳' },
  ESCALATE_HUMAN:   { bg: 'bg-red-500/15',     text: 'text-red-300',     border: 'border-red-500/40',     icon: '⚠' },
};

// ── Agent Config (extended for rebuttal agents) ───────────────────────────────
const AGENT_CONFIG: Record<string, { color: string; label: string; bg: string; border: string; dot: string }> = {
  advocate:           { color: 'text-emerald-400', label: 'Upstream Advocate',         bg: 'bg-emerald-500',    border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  advocate_rebuttal:  { color: 'text-emerald-300', label: 'Advocate — Rebuttal',       bg: 'bg-emerald-600',    border: 'border-emerald-400/30', dot: 'bg-emerald-300' },
  defender:           { color: 'text-rose-400',    label: 'Enterprise Defender',        bg: 'bg-rose-500',       border: 'border-rose-500/30',    dot: 'bg-rose-400' },
  defender_rebuttal:  { color: 'text-rose-300',    label: 'Defender — Rebuttal',        bg: 'bg-rose-600',       border: 'border-rose-400/30',    dot: 'bg-rose-300' },
  architect:          { color: 'text-indigo-400',  label: 'Architect Reviewer',         bg: 'bg-indigo-500',     border: 'border-indigo-500/30',  dot: 'bg-indigo-400' },
  judge:              { color: 'text-blue-400',    label: 'Verification Judge',         bg: 'bg-blue-500',       border: 'border-blue-500/30',    dot: 'bg-blue-400' },
};

// ── Types ─────────────────────────────────────────────────────────────────────
interface EvidenceItem {
  source: string;
  description: string;
  strength: number;
  line_start?: number;
  line_end?: number;
}

export default function DebateWorkspace() {
  const params = useParams();
  const debateId = Number(params.id);

  const [debate, setDebate] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const transcriptContainerRef = useRef<HTMLDivElement>(null);
  // Track whether the user is near the bottom so we don't hijack manual scrolling
  const isNearBottomRef = useRef(true);

  const fetchDebate = async () => {
    if (!debateId) return;
    try {
      const [dRes, mRes] = await Promise.all([
        axios.get(`${API_URL}/debates/${debateId}`),
        axios.get(`${API_URL}/debates/${debateId}/rounds`),
      ]);
      setDebate(dRes.data);
      setMessages(mRes.data ?? []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchDebate();
    const interval = setInterval(fetchDebate, 3000);
    return () => clearInterval(interval);
  }, [debateId]);

  // Listen for manual scroll to decide whether to keep auto-scrolling
  const handleScroll = useCallback(() => {
    const el = transcriptContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    // Consider "near bottom" if within 100px
    isNearBottomRef.current = distanceFromBottom < 100;
  }, []);

  // Only auto-scroll on new messages if the user hasn't scrolled up
  useEffect(() => {
    if (!isNearBottomRef.current) return;
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!debate) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-indigo-400 font-mono animate-pulse">Initializing Council Workspace...</p>
        </div>
      </div>
    );
  }

  const isCompleted = debate.status === 'completed';
  const isFailed    = debate.status === 'failed';
  const isEscalated = debate.status === 'escalated';

  const getStatusBadge = () => {
    if (isCompleted)  return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    if (isFailed)     return 'text-rose-400 bg-rose-400/10 border-rose-400/20';
    if (isEscalated)  return 'text-red-400 bg-red-400/10 border-red-400/20';
    return 'text-amber-400 bg-amber-400/10 border-amber-400/20 animate-pulse';
  };

  const getStatusLabel = () => {
    if (isCompleted)  return 'Consensus Reached';
    if (isFailed)     return 'Failed';
    if (isEscalated)  return '⚠ Escalated — Human Review Required';
    return 'Agents Deliberating…';
  };

  const safeParseMessage = (raw: string) => {
    try {
      if (typeof raw === 'object') return raw;
      return JSON.parse(raw);
    } catch {
      return { analysis: raw };
    }
  };

  // Group messages by round number for section dividers
  const messagesByRound: Record<number, any[]> = {};
  messages.forEach((msg) => {
    const r = msg.round ?? 0;
    if (!messagesByRound[r]) messagesByRound[r] = [];
    messagesByRound[r].push(msg);
  });
  const roundNumbers = Object.keys(messagesByRound)
    .map(Number)
    .sort((a, b) => a - b);

  // Resolution badge for Architect
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
              {resBadge && (
                <span className={`ml-3 px-2.5 py-0.5 rounded-full border text-[10px] font-black ${resBadge.bg} ${resBadge.text} ${resBadge.border}`}>
                  {resBadge.icon} {resolutionAction}
                </span>
              )}
            </h3>
            <p className="text-lg text-indigo-50 leading-relaxed font-medium">
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
            className="p-6 space-y-2 max-h-[900px] overflow-y-auto"
          >
            {messages.length === 0 ? (
              <div className="text-center text-neutral-500 font-mono py-16 flex flex-col items-center gap-4">
                <div className="w-8 h-8 border-2 border-neutral-700 border-t-neutral-400 rounded-full animate-spin" />
                <span>Agents are deliberating…</span>
              </div>
            ) : (
              roundNumbers.map((roundNum) => {
                const roundMsgs = messagesByRound[roundNum];
                const roundMeta = ROUND_LABELS[roundNum];

                return (
                  <div key={roundNum} className="space-y-4">
                    {/* ── Round Divider ───────────────────────────────────── */}
                    <div className={`bg-gradient-to-r ${roundMeta?.color ?? 'from-neutral-800/40 to-neutral-900/20'} rounded-xl px-5 py-3 flex items-center justify-between my-4 border border-white/5`}>
                      <div>
                        <p className="text-xs font-black text-white/80 uppercase tracking-widest">
                          {roundMeta?.label ?? `Round ${roundNum}`}
                        </p>
                        {roundMeta?.description && (
                          <p className="text-[11px] text-neutral-400 mt-0.5">{roundMeta.description}</p>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-neutral-600 bg-black/30 px-2.5 py-1 rounded-full border border-white/5">
                        {roundMsgs.length} msg{roundMsgs.length !== 1 ? 's' : ''}
                      </span>
                    </div>

                    {/* ── Messages in this Round ──────────────────────────── */}
                    {roundMsgs.map((msg: any, idx: number) => {
                      const content = safeParseMessage(msg.message);
                      const agent   = msg.agent as string;
                      const cfg     = AGENT_CONFIG[agent] ?? {
                        color: 'text-neutral-300',
                        label: agent,
                        bg: 'bg-neutral-700',
                        border: 'border-neutral-700',
                        dot: 'bg-neutral-400',
                      };
                      const evidenceRefs: EvidenceItem[] = Array.isArray(msg.evidence_refs) ? msg.evidence_refs : [];

                      // Detect the architect's resolution_action from message content
                      const msgResAction: string | undefined = content.resolution_action;
                      const msgResBadge = msgResAction ? RESOLUTION_STYLES[msgResAction] : null;

                      return (
                        <div
                          key={`${roundNum}-${idx}`}
                          id={`msg-${msg.id ?? `${roundNum}-${idx}`}`}
                          className={`bg-neutral-950/60 border ${cfg.border} rounded-2xl p-6 shadow-sm transition-all hover:border-opacity-60`}
                        >
                          {/* Agent header */}
                          <div className="flex flex-wrap justify-between items-center mb-4 gap-2">
                            <div className="flex items-center gap-3">
                              <div className={`w-9 h-9 rounded-full ${cfg.bg} flex items-center justify-center text-white text-sm font-black shadow-md`}>
                                {agent.charAt(0).toUpperCase()}
                              </div>
                              <div className="flex flex-col">
                                <span className={`font-bold uppercase tracking-wider text-sm ${cfg.color}`}>{cfg.label}</span>
                                {msg.timestamp && (
                                  <span className="text-[10px] text-neutral-600 font-mono">
                                    {new Date(msg.timestamp).toLocaleTimeString()}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {/* Resolution action badge on Architect card */}
                              {msgResBadge && (
                                <span
                                  id={`resolution-badge-${msg.id ?? idx}`}
                                  className={`px-3 py-1 rounded-full border text-[11px] font-black uppercase tracking-widest ${msgResBadge.bg} ${msgResBadge.text} ${msgResBadge.border}`}
                                >
                                  {msgResBadge.icon} {msgResAction}
                                </span>
                              )}
                              <span className="text-xs text-neutral-600 font-mono bg-neutral-900 px-3 py-1 rounded-full border border-neutral-800">
                                Round {msg.round}
                              </span>
                            </div>
                          </div>

                          {/* Message body */}
                          <div className="text-neutral-300 leading-relaxed text-[15px] pl-12 space-y-3">
                            {/* Rebuttal-specific fields */}
                            {(agent === 'advocate_rebuttal' || agent === 'defender_rebuttal') && (
                              <div className="space-y-3">
                                {content.rebuttal && (
                                  <p>{content.rebuttal}</p>
                                )}
                                {content.conceded_points?.length > 0 && (
                                  <div className="bg-emerald-950/30 border border-emerald-700/30 rounded-lg p-3">
                                    <p className="text-[10px] font-black text-emerald-500 uppercase tracking-widest mb-1">Conceded Points</p>
                                    <ul className="list-disc list-inside space-y-0.5 text-sm text-emerald-200/70">
                                      {content.conceded_points.map((pt: string, i: number) => <li key={i}>{pt}</li>)}
                                    </ul>
                                  </div>
                                )}
                                {content.contested_points?.length > 0 && (
                                  <div className="bg-rose-950/30 border border-rose-700/30 rounded-lg p-3">
                                    <p className="text-[10px] font-black text-rose-500 uppercase tracking-widest mb-1">Contested Points</p>
                                    <ul className="list-disc list-inside space-y-0.5 text-sm text-rose-200/70">
                                      {content.contested_points.map((pt: string, i: number) => <li key={i}>{pt}</li>)}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Architect-specific fields */}
                            {agent === 'architect' && (
                              <div className="space-y-3">
                                {content.rationale && <p>{content.rationale}</p>}
                                {content.implementation_steps?.length > 0 && (
                                  <div className="bg-indigo-950/30 border border-indigo-700/30 rounded-lg p-3">
                                    <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-2">Implementation Steps</p>
                                    <ol className="list-decimal list-inside space-y-1.5 text-sm text-indigo-200/80">
                                      {content.implementation_steps.map((step: string, i: number) => <li key={i}>{step}</li>)}
                                    </ol>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Judge-specific fields */}
                            {agent === 'judge' && (
                              <div className="space-y-3">
                                <p>{content.verification_summary ?? content.analysis ?? '—'}</p>
                                {content.invalidated_claims?.length > 0 && (
                                  <div className="bg-rose-950/30 border border-rose-700/30 rounded-lg p-3">
                                    <p className="text-[10px] font-black text-rose-400 uppercase tracking-widest mb-1">Invalidated Claims</p>
                                    <ul className="list-disc list-inside space-y-1 text-sm text-rose-200/70">
                                      {content.invalidated_claims.map((claim: string, i: number) => <li key={i}>{claim}</li>)}
                                    </ul>
                                  </div>
                                )}
                                {content.adjusted_confidence_penalty != null && (
                                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-rose-950/40 border border-rose-900/50 rounded-lg text-sm">
                                    <span className="text-rose-400 font-bold text-xs uppercase tracking-wider">Confidence Penalty</span>
                                    <span className="text-rose-300 font-mono">−{(content.adjusted_confidence_penalty * 100).toFixed(0)}%</span>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Default: advocate / defender initial analysis */}
                            {agent !== 'architect' && agent !== 'judge' && agent !== 'advocate_rebuttal' && agent !== 'defender_rebuttal' && (
                              <p>{content.analysis ?? content.content ?? '—'}</p>
                            )}

                            {/* ── Evidence Refs (with line-range chips) ──── */}
                            {evidenceRefs.length > 0 && (
                              <div className="mt-5 pt-5 border-t border-neutral-800/50">
                                <p className="text-[10px] font-black text-neutral-600 uppercase tracking-widest mb-3">Evidence Cited</p>
                                <ul className="space-y-2">
                                  {evidenceRefs.map((ev: EvidenceItem, i: number) => (
                                    <li
                                      key={i}
                                      className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-l-2 border-emerald-500/60 pl-3 bg-neutral-900/50 py-2 pr-3 rounded-r-lg text-sm"
                                    >
                                      <div className="flex flex-col gap-1 flex-1">
                                        {/* Source tag */}
                                        {ev.source && (
                                          <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider">{ev.source}</span>
                                        )}
                                        <span className="text-neutral-300">{ev.description ?? String(ev)}</span>
                                      </div>
                                      <div className="flex items-center gap-2 shrink-0">
                                        {/* Line-range chip linking to diff viewer */}
                                        {ev.line_start != null && ev.line_end != null && (
                                          <a
                                            href={`#diff-viewer`}
                                            id={`line-chip-${msg.id ?? idx}-${i}`}
                                            className="text-[11px] font-mono px-2 py-0.5 rounded border border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 transition-colors whitespace-nowrap"
                                            title={`Jump to lines ${ev.line_start}–${ev.line_end} in diff`}
                                          >
                                            L{ev.line_start}–{ev.line_end}
                                          </a>
                                        )}
                                        {ev.strength != null && (
                                          <span className="text-emerald-400 font-mono text-xs bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 whitespace-nowrap">
                                            {Number(ev.strength).toFixed(2)}
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
                      );
                    })}
                  </div>
                );
              })
            )}

            {!isCompleted && !isFailed && !isEscalated && (
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
