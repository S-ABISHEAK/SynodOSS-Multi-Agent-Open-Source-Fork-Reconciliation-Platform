import { useState, useMemo } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function ConflictTable({ conflicts }: { conflicts: any[] }) {
  const router = useRouter();
  const [loadingUnitId, setLoadingUnitId] = useState<number | null>(null);
  
  // Filtering states
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [filterType, setFilterType] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'complexity' | 'severity' | 'none'>('none');

  const getSeverityWeight = (sev: string) => {
    switch(sev?.toUpperCase()) {
      case 'CRITICAL': return 4;
      case 'HIGH': return 3;
      case 'MEDIUM': return 2;
      case 'LOW': return 1;
      default: return 0;
    }
  };

  const filteredAndSortedConflicts = useMemo(() => {
    if (!conflicts) return [];
    
    let result = conflicts.filter(c => {
      const matchSev = filterSeverity === 'ALL' || c.severity?.toUpperCase() === filterSeverity;
      const matchType = filterType === 'ALL' || c.conflict_type?.toUpperCase() === filterType;
      return matchSev && matchType;
    });

    if (sortBy === 'complexity') {
      result.sort((a, b) => (b.complexity_score || 0) - (a.complexity_score || 0));
    } else if (sortBy === 'severity') {
      result.sort((a, b) => getSeverityWeight(b.severity) - getSeverityWeight(a.severity));
    }

    return result;
  }, [conflicts, filterSeverity, filterType, sortBy]);

  if (!conflicts || conflicts.length === 0) {
    return (
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-8 text-center text-neutral-400">
        No reconciliation conflicts detected.
      </div>
    );
  }

  const getSeverityColor = (sev: string) => {
    switch(sev?.toUpperCase()) {
      case 'CRITICAL': return 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
      case 'HIGH': return 'bg-orange-500/10 text-orange-400 border border-orange-500/20';
      case 'MEDIUM': return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
      case 'LOW': return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      default: return 'bg-neutral-800 text-neutral-300';
    }
  }

  const handleStartDebate = async (unitId: number) => {
    if (!unitId) return;
    setLoadingUnitId(unitId);
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await axios.post(`${API_URL}/debates/start?unit_id=${unitId}`);
      const debateId = res.data.debate_id;
      router.push(`/debate/${debateId}`);
    } catch (e) {
      console.error(e);
      setLoadingUnitId(null);
    }
  };

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden flex flex-col">
      <div className="p-4 border-b border-neutral-800 flex flex-col sm:flex-row justify-between items-center gap-4">
        <h3 className="text-lg font-semibold text-white">Detected Conflicts</h3>
        
        <div className="flex flex-wrap gap-3">
          <select 
            value={filterSeverity} 
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-neutral-950 border border-neutral-800 text-neutral-300 text-xs rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          
          <select 
            value={filterType} 
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-neutral-950 border border-neutral-800 text-neutral-300 text-xs rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="ALL">All Types</option>
            <option value="LOGIC">Logic</option>
            <option value="FORMATTING">Formatting</option>
            <option value="ARCHITECTURE">Architecture</option>
          </select>
          
          <select 
            value={sortBy} 
            onChange={(e) => setSortBy(e.target.value as any)}
            className="bg-neutral-950 border border-neutral-800 text-neutral-300 text-xs rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="none">Sort By...</option>
            <option value="severity">Highest Severity</option>
            <option value="complexity">Highest Complexity</option>
          </select>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-neutral-300">
          <thead className="text-xs text-neutral-500 uppercase bg-neutral-950/50">
            <tr>
              <th className="px-6 py-4 font-medium">File Path</th>
              <th className="px-6 py-4 font-medium">Type</th>
              <th className="px-6 py-4 font-medium">Severity</th>
              <th className="px-6 py-4 font-medium">Complexity</th>
              <th className="px-6 py-4 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800">
            {filteredAndSortedConflicts.map((c) => (
              <tr key={c.id} className="hover:bg-neutral-800/50 transition-colors">
                <td className="px-6 py-4 font-mono text-xs max-w-[200px] truncate" title={c.file_path}>{c.file_path}</td>
                <td className="px-6 py-4 capitalize">{c.conflict_type?.toLowerCase()}</td>
                <td className="px-6 py-4">
                  <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${getSeverityColor(c.severity)}`}>
                    {c.severity}
                  </span>
                </td>
                <td className="px-6 py-4 text-xs">
                  {c.complexity_score?.toFixed(1) || '0.0'}
                </td>
                <td className="px-6 py-4 text-right">
                  {c.debate_id ? (
                    <Link href={`/debate/${c.debate_id}`} className="px-4 py-2 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 rounded-md text-xs font-semibold transition-colors">
                      View Debate
                    </Link>
                  ) : c.unit_id ? (
                    <button 
                      onClick={() => handleStartDebate(c.unit_id)}
                      disabled={loadingUnitId === c.unit_id}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-xs font-semibold transition-colors disabled:opacity-50"
                    >
                      {loadingUnitId === c.unit_id ? 'Starting...' : 'Start Debate'}
                    </button>
                  ) : (
                    <span className="text-xs text-neutral-500">N/A</span>
                  )}
                </td>
              </tr>
            ))}
            {filteredAndSortedConflicts.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-neutral-500 italic">
                  No conflicts match the selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
