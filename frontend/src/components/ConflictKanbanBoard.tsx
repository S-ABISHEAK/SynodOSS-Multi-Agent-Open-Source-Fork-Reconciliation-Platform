import React from 'react';
import Link from 'next/link';

interface ConflictKanbanProps {
  conflicts: any[];
  onStartDebate: (unitId: number) => void;
  debatingUnits: Record<number, boolean>;
}

export default function ConflictKanbanBoard({ conflicts, onStartDebate, debatingUnits }: ConflictKanbanProps) {
  // Define columns
  const columns = [
    { id: 'pending', title: 'Pending Review' },
    { id: 'in_progress', title: 'Actively Debating' },
    { id: 'completed', title: 'Consensus Reached' },
    { id: 'failed', title: 'Escalated / Failed' },
  ];

  // Group conflicts by debate_status
  const getColumnConflicts = (colId: string) => {
    return conflicts.filter(c => {
      if (colId === 'pending' && !c.debate_status) return true;
      if (colId === 'in_progress' && (c.debate_status === 'in_progress' || c.debate_status === 'active')) return true;
      return c.debate_status === colId;
    });
  };

  const getSeverityColor = (sev: string) => {
    switch(sev?.toLowerCase()) {
      case 'critical': return 'text-red-400 bg-red-400/10 border-red-400/20';
      case 'high': return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
      default: return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 overflow-x-auto pb-4">
      {columns.map(col => {
        const colConflicts = getColumnConflicts(col.id);
        return (
          <div key={col.id} className="flex flex-col bg-neutral-900/50 border border-neutral-800 rounded-lg overflow-hidden min-w-[300px]">
            <div className="p-3 bg-neutral-900 border-b border-neutral-800 flex justify-between items-center">
              <h3 className="font-semibold text-neutral-300">{col.title}</h3>
              <span className="bg-neutral-800 text-neutral-400 text-xs px-2 py-0.5 rounded-full">
                {colConflicts.length}
              </span>
            </div>
            
            <div className="flex-1 p-3 space-y-3 min-h-[500px]">
              {colConflicts.map(c => (
                <div key={c.id} className="bg-neutral-800/50 border border-neutral-700/50 p-4 rounded-lg flex flex-col gap-3 shadow-sm hover:border-neutral-600 transition-colors">
                  <div className="flex justify-between items-start">
                    <span className="font-mono text-xs text-neutral-400 truncate max-w-[70%]" title={c.file_path}>
                      {c.file_path.split('/').pop()}
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border uppercase tracking-wider ${getSeverityColor(c.severity)}`}>
                      {c.severity}
                    </span>
                  </div>
                  
                  <p className="text-sm text-neutral-300 line-clamp-2">
                    {c.summary}
                  </p>
                  
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-neutral-500">
                      Complexity: {c.complexity_score?.toFixed(1) || '0.0'}
                    </span>
                    
                    {col.id === 'pending' && c.unit_id ? (
                      <button
                        onClick={() => onStartDebate(c.unit_id)}
                        disabled={debatingUnits[c.unit_id]}
                        className="text-xs bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 px-3 py-1 rounded transition-colors disabled:opacity-50"
                      >
                        {debatingUnits[c.unit_id] ? 'Starting...' : 'Start Debate'}
                      </button>
                    ) : null}

                    {c.debate_id && (
                      <Link 
                        href={`/debate/${c.debate_id}`}
                        className="text-xs text-emerald-400 hover:text-emerald-300 underline underline-offset-2"
                      >
                        View Debate
                      </Link>
                    )}
                  </div>
                </div>
              ))}
              
              {colConflicts.length === 0 && (
                <div className="h-full flex items-center justify-center text-sm text-neutral-600 italic">
                  No conflicts
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
