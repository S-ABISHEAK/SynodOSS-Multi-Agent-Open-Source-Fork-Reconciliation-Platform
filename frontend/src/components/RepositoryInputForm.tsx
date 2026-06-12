import { useState } from 'react';
import { startScan } from '@/services/api';
import { Button } from '@/components/ui/button';

export default function RepositoryInputForm({ onScanStarted }: { onScanStarted: (id: number) => void }) {
  const [upstream, setUpstream] = useState('');
  const [fork, setFork] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await startScan(upstream, fork);
      onScanStarted(res.scan_id);
    } catch (e) {
      console.error(e);
      alert('Failed to start scan');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-neutral-300 mb-1">Upstream Repository URL</label>
          <input 
            type="url" 
            required 
            value={upstream} 
            onChange={e => setUpstream(e.target.value)}
            className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 text-neutral-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
            placeholder="https://github.com/torvalds/linux"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-300 mb-1">Fork Repository URL</label>
          <input 
            type="url" 
            required 
            value={fork} 
            onChange={e => setFork(e.target.value)}
            className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 text-neutral-100 focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 outline-none transition-all"
            placeholder="https://github.com/my-org/linux-fork"
          />
        </div>
      </div>
      <Button 
        type="submit"
        disabled={loading}
        className="w-full bg-white text-black hover:bg-neutral-200 py-6 text-lg font-semibold rounded-lg transition-colors"
      >
        {loading ? 'Initializing...' : 'Start Intelligence Scan'}
      </Button>
    </form>
  );
}
