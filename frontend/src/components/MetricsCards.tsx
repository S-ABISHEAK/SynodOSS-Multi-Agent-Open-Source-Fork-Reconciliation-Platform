export default function MetricsCards({ summary }: { summary: any }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-xl flex flex-col justify-center items-center text-center space-y-2">
        <span className="text-neutral-400 text-sm font-medium uppercase tracking-wider">Commit Gap</span>
        <span className="text-4xl font-black text-white">{summary.commit_gap}</span>
      </div>
      <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-xl flex flex-col justify-center items-center text-center space-y-2">
        <span className="text-neutral-400 text-sm font-medium uppercase tracking-wider">Changed Files</span>
        <span className="text-4xl font-black text-emerald-400">{summary.changed_files}</span>
      </div>
      <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-xl flex flex-col justify-center items-center text-center space-y-2">
        <span className="text-neutral-400 text-sm font-medium uppercase tracking-wider">Detected Conflicts</span>
        <span className="text-4xl font-black text-rose-400">{summary.conflicts?.length || 0}</span>
      </div>
    </div>
  )
}
