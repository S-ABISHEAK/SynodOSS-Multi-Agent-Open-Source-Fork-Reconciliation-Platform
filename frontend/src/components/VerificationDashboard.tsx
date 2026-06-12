import React from 'react';

export default function VerificationDashboard({ debate, messages }: { debate: Record<string, unknown>, messages: Record<string, unknown>[] }) {
  const judgeMsg = messages.find((m) => m.agent === 'judge');
  const content = judgeMsg ? (typeof judgeMsg.message === 'string' ? JSON.parse(judgeMsg.message) : judgeMsg.message) : null;
  
  const verifiedCount = content?.verified_evidence_count ?? 0;
  const invalidatedClaims = content?.invalidated_claims ?? [];
  
  const score = debate.verification_score != null ? Math.round(debate.verification_score * 100) : '--';
  const color = typeof score === 'number' && score >= 80 ? 'text-emerald-400' : (typeof score === 'number' && score >= 50 ? 'text-amber-400' : 'text-rose-400');

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5 shadow-lg">
      <h3 className="text-xs font-black text-neutral-400 uppercase tracking-widest mb-4">Verification Dashboard</h3>
      
      <div className="flex items-center justify-between mb-6 bg-neutral-950 p-4 rounded-xl border border-neutral-800">
        <span className="text-sm font-bold text-neutral-400 uppercase tracking-widest">Trust Score</span>
        <span className={`text-4xl font-black ${color}`}>{score}%</span>
      </div>

      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-sm text-neutral-500">Claims Verified</span>
          <span className="text-sm font-bold text-emerald-400">{verifiedCount}</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-sm text-neutral-500">Invalidated Claims</span>
          <span className="text-sm font-bold text-rose-400">{invalidatedClaims.length}</span>
        </div>

        {invalidatedClaims.length > 0 && (
          <div className="mt-2 bg-rose-950/20 border border-rose-900/40 rounded-lg p-3">
             <ul className="list-disc pl-4 space-y-1 text-xs text-rose-300">
               {invalidatedClaims.map((claim: string, i: number) => (
                 <li key={i}>{claim}</li>
               ))}
             </ul>
          </div>
        )}
      </div>
    </div>
  );
}
