'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getScanStatus, getScanSummary, getScanConflicts, startDebate } from '@/services/api';
import ScanProgress from '@/components/ScanProgress';
import MetricsCards from '@/components/MetricsCards';
import ConflictTable from '@/components/ConflictTable';
import ConflictKanbanBoard from '@/components/ConflictKanbanBoard';

export default function ScanDetail() {
  const params = useParams();
  const router = useRouter();
  const scanId = Number(params.id);
  const [status, setStatus] = useState<string>('pending');
  const [progress, setProgress] = useState(0);
  const [summary, setSummary] = useState<any>(null);
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [viewMode, setViewMode] = useState<'table' | 'kanban'>('kanban');
  const [debatingUnits, setDebatingUnits] = useState<Record<number, boolean>>({});

  const handleStartDebate = async (unitId: number) => {
    try {
      setDebatingUnits(prev => ({ ...prev, [unitId]: true }));
      const res = await startDebate(unitId);
      if (res && res.debate_id) {
        // Optimistically update the conflict locally to show it's in progress
        setConflicts(prev => prev.map(c => 
          c.unit_id === unitId 
            ? { ...c, debate_id: res.debate_id, debate_status: 'in_progress' } 
            : c
        ));
      }
    } catch (e) {
      console.error(e);
      setDebatingUnits(prev => ({ ...prev, [unitId]: false }));
    }
  };

  useEffect(() => {
    if (!scanId) return;

    const fetchConflicts = async () => {
      const confs = await getScanConflicts(scanId);
      setConflicts(confs);
    }

    const interval = setInterval(async () => {
      try {
        const statusData = await getScanStatus(scanId);
        setStatus(statusData.status);
        setProgress(statusData.progress);

        if (statusData.status === 'completed' || statusData.status === 'failed') {
          // If it just finished, fetch summary and conflicts
          if (!summary && statusData.status === 'completed') {
            const sum = await getScanSummary(scanId);
            setSummary(sum);
          }
          await fetchConflicts();
          // Keep polling conflicts slowly to update Kanban board statuses
        }
      } catch (e) {
        console.error(e);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [scanId, summary]);

  return (
    <div className="min-h-screen bg-black text-white p-8">
      <main className="max-w-7xl mx-auto space-y-8 mt-8">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight">Scan Details #{scanId}</h1>
          
          {status === 'completed' && (
            <div className="flex bg-neutral-900 border border-neutral-800 rounded-lg p-1">
              <button 
                onClick={() => setViewMode('kanban')}
                className={`px-4 py-1.5 rounded-md text-sm transition-colors ${viewMode === 'kanban' ? 'bg-neutral-800 text-white shadow-sm' : 'text-neutral-400 hover:text-neutral-200'}`}
              >
                Kanban
              </button>
              <button 
                onClick={() => setViewMode('table')}
                className={`px-4 py-1.5 rounded-md text-sm transition-colors ${viewMode === 'table' ? 'bg-neutral-800 text-white shadow-sm' : 'text-neutral-400 hover:text-neutral-200'}`}
              >
                Table
              </button>
            </div>
          )}
        </div>
        
        {status !== 'completed' && status !== 'failed' && (
           <ScanProgress progress={progress} status={status} />
        )}

        {status === 'failed' && (
           <div className="bg-red-900/20 text-red-400 p-4 rounded-lg border border-red-900/50">
             Scan failed to complete. Please check the logs.
           </div>
        )}

        {status === 'completed' && summary && (
           <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
             <MetricsCards summary={summary} />
             
             {viewMode === 'kanban' ? (
               <ConflictKanbanBoard 
                 conflicts={conflicts} 
                 onStartDebate={handleStartDebate} 
                 debatingUnits={debatingUnits}
               />
             ) : (
               <ConflictTable conflicts={conflicts} />
             )}
           </div>
        )}
      </main>
    </div>
  );
}
