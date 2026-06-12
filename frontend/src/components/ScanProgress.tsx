export default function ScanProgress({ progress, status }: { progress: number, status: string }) {
  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 space-y-4">
      <div className="flex justify-between items-center text-sm font-medium">
        <span className="text-neutral-300">Scan Status: <span className="text-white capitalize">{status}</span></span>
        <span className="text-blue-400">{progress}%</span>
      </div>
      <div className="w-full bg-neutral-800 h-2 rounded-full overflow-hidden">
         <div 
           className="bg-blue-500 h-full transition-all duration-500 ease-out" 
           style={{ width: `${progress}%` }}
         />
      </div>
      <p className="text-xs text-neutral-500 text-center animate-pulse">
        {status === 'running' ? 'Analyzing repository histories and computing divergence...' : 'Initializing...'}
      </p>
    </div>
  )
}
