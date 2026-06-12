import React, { useState } from 'react';

interface InteractiveDiffViewerProps {
  diffHunk: string;
  filePath: string;
}

export default function InteractiveDiffViewer({ diffHunk, filePath }: InteractiveDiffViewerProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!diffHunk) return null;

  const lines = diffHunk.split('\n');

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden mt-6 shadow-lg shadow-black/50">
      <div 
        className="p-4 flex justify-between items-center bg-neutral-950/50 cursor-pointer hover:bg-neutral-800/50 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-3">
          <svg className={`w-5 h-5 text-neutral-400 transition-transform ${isOpen ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <h3 className="text-sm font-medium text-white flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            Code Context
          </h3>
        </div>
        <span className="text-xs font-mono text-neutral-500 bg-neutral-900 px-3 py-1 rounded-md border border-neutral-800 truncate max-w-[250px] sm:max-w-[400px]">
          {filePath}
        </span>
      </div>

      {isOpen && (
        <div className="border-t border-neutral-800 overflow-x-auto p-4 bg-[#0d1117]">
          <pre className="text-[13px] font-mono leading-relaxed">
            {lines.map((line, idx) => {
              let lineClass = 'text-neutral-300';
              let bgClass = 'hover:bg-neutral-800/30';
              let prefix = ' ';

              if (line.startsWith('+')) {
                lineClass = 'text-emerald-400';
                bgClass = 'bg-emerald-900/20 hover:bg-emerald-900/30';
                prefix = '+';
              } else if (line.startsWith('-')) {
                lineClass = 'text-rose-400';
                bgClass = 'bg-rose-900/20 hover:bg-rose-900/30';
                prefix = '-';
              } else if (line.startsWith('@@')) {
                lineClass = 'text-indigo-400 font-semibold';
                bgClass = 'bg-indigo-900/10';
              }

              return (
                <div key={idx} className={`flex px-2 py-0.5 rounded-sm ${bgClass}`}>
                  <span className={`select-none pr-4 w-6 text-right opacity-50 ${lineClass}`}>
                    {prefix}
                  </span>
                  <span className={`${lineClass} whitespace-pre-wrap break-all`}>
                    {line.startsWith('+') || line.startsWith('-') ? line.substring(1) : line}
                  </span>
                </div>
              );
            })}
          </pre>
        </div>
      )}
    </div>
  );
}
