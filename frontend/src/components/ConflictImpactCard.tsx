import React from 'react';

export default function ConflictImpactCard({ unit }: { unit: Record<string, unknown> | null }) {
  if (!unit) return null;

  const callers = Array.isArray(unit.callers) ? unit.callers : [];
  const dependencies = Array.isArray(unit.dependencies) ? unit.dependencies : [];

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5 shadow-lg">
      <h3 className="text-xs font-black text-neutral-400 uppercase tracking-widest mb-4">Architectural Impact</h3>
      
      <div className="space-y-4">
        <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
          <span className="text-sm text-neutral-500">Layer Affected</span>
          <span className="text-sm font-bold text-indigo-400">{unit.architectural_layer || 'Unknown'}</span>
        </div>
        
        <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
          <span className="text-sm text-neutral-500">Symbol Modified</span>
          <span className="text-sm font-mono text-emerald-400">{unit.symbol || 'Unknown'}</span>
        </div>

        <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
          <span className="text-sm text-neutral-500">Type</span>
          <span className="text-xs font-bold text-amber-400 uppercase bg-amber-500/10 px-2 py-0.5 rounded-full">{unit.symbol_type || 'Unknown'}</span>
        </div>

        <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
          <span className="text-sm text-neutral-500">Callers Affected</span>
          <span className="text-sm font-bold text-white">{callers.length}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm text-neutral-500">Dependencies</span>
          <div className="flex gap-1 flex-wrap justify-end max-w-[60%]">
            {dependencies.length === 0 ? (
              <span className="text-sm font-bold text-white">None</span>
            ) : (
              dependencies.map((d: string, i: number) => (
                <span key={i} className="text-[10px] font-mono text-neutral-300 bg-neutral-800 px-1.5 py-0.5 rounded border border-neutral-700">{d}</span>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
