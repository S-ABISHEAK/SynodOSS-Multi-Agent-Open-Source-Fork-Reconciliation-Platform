import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'wouter';
import { Header } from '@/components/Header';
import { GlassCard } from '@/components/glass/GlassCard';
import { GlassBadge } from '@/components/glass/GlassBadge';
import { MetricCard } from '@/components/MetricCard';
import { LoadingSpinner } from '@/components/glass/LoadingSpinner';
import { debateApi, handleApiError } from '@/lib/api';
import { toast } from 'sonner';
import { Brain, CheckCircle, AlertCircle, MessageSquare, Code2 } from 'lucide-react';

interface DebateRound {
  round: number;
  agent: string;
  message: string;
}

interface DebateData {
  status: string;
  confidence?: number;
  verification_score?: number;
  evidence_count?: number;
  architectural_proposal?: string;
  resolution_action?: string;
  diff_hunk?: string;
  file_path?: string;
}

export default function DebateWorkspace() {
  const { id: debateId } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [debateData, setDebateData] = useState<DebateData | null>(null);
  const [rounds, setRounds] = useState<DebateRound[]>([]);
  const [debateStatus, setDebateStatus] = useState<string>('pending');
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadDebate = async () => {
      if (!debateId) return;

      try {
        const debateIdNum = parseInt(debateId);

        // Load debate status
        const data = await debateApi.getDebateStatus(debateIdNum);
        setDebateData(data);
        setDebateStatus(data.status);

        // Load debate rounds
        const roundsData = await debateApi.getDebateRounds(debateIdNum);
        setRounds(roundsData);
      } catch (error) {
        const message = handleApiError(error);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    };

    loadDebate();

    // Poll for updates if debate is still running
    const interval = setInterval(() => {
      if (debateStatus === 'pending' || debateStatus === 'in_progress') {
        loadDebate();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [debateId, debateStatus]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [rounds]);

  const getAgentColor = (agent: string) => {
    const lower = agent.toLowerCase();
    if (lower.includes('advocate')) return 'advocate';
    if (lower.includes('defender')) return 'defender';
    if (lower.includes('architect')) return 'architect';
    if (lower.includes('judge')) return 'judge';
    return 'low';
  };

  const getAgentIcon = (agent: string) => {
    const lower = agent.toLowerCase();
    if (lower.includes('advocate')) return '🛡️';
    if (lower.includes('defender')) return '⚔️';
    if (lower.includes('architect')) return '🏗️';
    if (lower.includes('judge')) return '⚖️';
    return '🤖';
  };

  const parseMessage = (messageStr: string) => {
    try {
      return JSON.parse(messageStr);
    } catch {
      return { analysis: messageStr };
    }
  };

  if (loading) {
    return (
      <div className="ambient-bg">
        <Header title={`Debate #${debateId}`} />
        <main className="container mx-auto px-4 py-12 flex justify-center">
          <LoadingSpinner message="Loading debate workspace..." />
        </main>
      </div>
    );
  }

  return (
    <div className="ambient-bg">
      <Header title={`Debate #${debateId}`} />

      <main className="container mx-auto px-4 py-12 max-w-7xl">
        {/* Status & Metrics Row */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-6">
            <GlassBadge
              variant={
                debateStatus === 'completed'
                  ? 'low'
                  : debateStatus === 'failed'
                  ? 'critical'
                  : debateStatus === 'escalated'
                  ? 'medium'
                  : 'medium'
              }
            >
              {debateStatus.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </GlassBadge>
            {debateStatus === 'in_progress' && (
              <span className="text-sm text-amber-300 font-medium flex items-center gap-2">
                <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
                Agents Deliberating...
              </span>
            )}
          </div>

          {debateData && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard
                label="Confidence"
                value={`${Math.round((debateData.confidence || 0) * 100)}%`}
                icon={<Brain className="w-5 h-5" />}
                color="indigo"
              />
              <MetricCard
                label="Verification"
                value={`${Math.round((debateData.verification_score || 0) * 100)}%`}
                icon={<CheckCircle className="w-5 h-5" />}
                color="emerald"
              />
              <MetricCard
                label="Evidence"
                value={debateData.evidence_count || 0}
                unit="refs"
                icon={<AlertCircle className="w-5 h-5" />}
                color="amber"
              />
              <MetricCard
                label="Status"
                value={debateStatus === 'completed' ? 'Done' : 'Active'}
                icon={<MessageSquare className="w-5 h-5" />}
                color={debateStatus === 'completed' ? 'emerald' : 'amber'}
              />
            </div>
          )}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Debate Transcript (Center/Full) */}
          <div className="lg:col-span-2">
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-indigo-400" />
              Debate Transcript
            </h3>

            <div
              ref={feedRef}
              className="glass-card p-6 h-96 overflow-y-auto space-y-4 mb-4"
            >
              {rounds.length === 0 && debateStatus === 'pending' ? (
                <div className="flex items-center justify-center h-full">
                  <LoadingSpinner size="md" message="Waiting for agents..." />
                </div>
              ) : rounds.length === 0 ? (
                <p className="text-white/60 text-center py-12">No messages yet.</p>
              ) : (
                rounds.map((round, idx) => {
                  const msg = parseMessage(round.message);
                  const agentColor = getAgentColor(round.agent);
                  const agentIcon = getAgentIcon(round.agent);

                  return (
                    <div key={idx} className="animate-in fade-in slide-in-from-bottom-2">
                      <GlassCard className={`p-4 border-l-2 agent-${agentColor}`}>
                        <div className="flex items-start gap-3">
                          <span className="text-2xl">{agentIcon}</span>
                          <div className="flex-1">
                            <p className="font-semibold text-white mb-2">
                              {round.agent.charAt(0).toUpperCase() + round.agent.slice(1)}
                              <span className="text-xs text-white/40 ml-2">Round {round.round}</span>
                            </p>
                            {msg.analysis && (
                              <p className="text-sm text-white/80 mb-2">{msg.analysis}</p>
                            )}
                            {msg.implementation_steps && Array.isArray(msg.implementation_steps) && (
                              <ul className="text-xs text-white/70 space-y-1 ml-4">
                                {msg.implementation_steps.map((step: string, i: number) => (
                                  <li key={i}>• {step}</li>
                                ))}
                              </ul>
                            )}
                            {msg.evidence_refs && Array.isArray(msg.evidence_refs) && (
                              <div className="text-xs text-indigo-300 mt-2 flex flex-wrap gap-1">
                                {msg.evidence_refs.map((ref: string, i: number) => (
                                  <span key={i} className="bg-indigo-500/20 px-2 py-1 rounded">
                                    {ref}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </GlassCard>
                    </div>
                  );
                })
              )}

              {debateStatus === 'running' && rounds.length > 0 && (
                <div className="flex justify-center py-4">
                  <LoadingSpinner size="sm" message="" />
                </div>
              )}
            </div>
          </div>

          {/* Architectural Proposal (Right Sidebar) */}
          <div>
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Code2 className="w-5 h-5 text-emerald-400" />
              Proposal
            </h3>

            {debateStatus === 'completed' && debateData?.architectural_proposal ? (
              <GlassCard className="p-6 border-l-2 border-l-emerald-500/50 h-96 overflow-y-auto">
                <div className="space-y-4">
                  <div>
                    <p className="text-xs text-white/60 font-semibold mb-2">RESOLUTION</p>
                    <p className="text-sm text-white/80">
                      {debateData.architectural_proposal}
                    </p>
                  </div>

                  {debateData.resolution_action && (
                    <div className="pt-4 border-t border-white/10">
                      <p className="text-xs text-white/60 font-semibold mb-2">ACTION</p>
                      <p className="text-sm text-emerald-200 font-mono">
                        {debateData.resolution_action}
                      </p>
                    </div>
                  )}

                  <div className="pt-4 border-t border-white/10">
                    <p className="text-xs text-white/60 font-semibold mb-2">CONFIDENCE</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-emerald-500 to-indigo-500"
                          style={{
                            width: `${(debateData.confidence || 0) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-emerald-300">
                        {Math.round((debateData.confidence || 0) * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              </GlassCard>
            ) : debateStatus === 'running' ? (
              <GlassCard className="p-6 h-96 flex items-center justify-center">
                <div className="text-center">
                  <LoadingSpinner size="md" message="Generating proposal..." />
                </div>
              </GlassCard>
            ) : (
              <GlassCard className="p-6 h-96 flex items-center justify-center">
                <p className="text-white/60 text-center">
                  {debateStatus === 'failed'
                    ? 'Debate failed. No proposal available.'
                    : 'Waiting for debate to complete...'}
                </p>
              </GlassCard>
            )}
          </div>
        </div>

        {/* Diff Viewer Section */}
        <div>
          <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Code2 className="w-5 h-5 text-amber-400" />
            Conflict Diff {debateData?.file_path && <span className="text-sm font-normal text-white/50">({debateData.file_path})</span>}
          </h3>

          <GlassCard className="p-6 bg-black/40 border-amber-500/20 max-h-96 overflow-y-auto">
            <pre className="text-xs text-amber-100 font-mono whitespace-pre-wrap">
              {debateData?.diff_hunk || 'No diff available.'}
            </pre>
          </GlassCard>
        </div>
      </main>
    </div>
  );
}
