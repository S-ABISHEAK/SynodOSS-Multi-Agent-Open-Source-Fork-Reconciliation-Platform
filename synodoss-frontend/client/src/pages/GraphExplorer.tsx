import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useLocation } from 'wouter';
import { motion } from 'framer-motion';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  Handle,
  Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { scanApi, handleApiError } from '@/lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Box, Link as LinkIcon, FileText, Database, Activity, Code2, AlertCircle } from 'lucide-react';
import { Header } from '@/components/Header';
import { MetricCard } from '@/components/MetricCard';
import { GlassCard } from '@/components/glass/GlassCard';
import { LoadingSpinner } from '@/components/glass/LoadingSpinner';

// Custom Node for Symbols
const SymbolNode = ({ data }: any) => {
  const isFunction = data.nodeType === 'FUNCTION';
  const isClass = data.nodeType === 'CLASS';
  const color = isFunction ? 'bg-blue-500' : isClass ? 'bg-emerald-500' : 'bg-orange-500';

  return (
    <div className="px-4 py-2 shadow-lg rounded-xl border border-white/20 bg-black/60 backdrop-blur-md">
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 rounded-full ${color}`} />
        <div>
          <div className="text-sm font-bold text-white">{data.label}</div>
          <div className="text-xs text-white/50">{data.nodeType}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </div>
  );
};

const nodeTypes = {
  symbolNode: SymbolNode,
};

export default function GraphExplorer() {
  const [, navigate] = useLocation();
  const { id: scanId } = useParams<{ id: string }>();
  
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState<any>(null);
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [ragData, setRagData] = useState<any>(null);
  const [loadingRag, setLoadingRag] = useState(false);

  useEffect(() => {
    const loadGraph = async () => {
      if (!scanId) return;
      try {
        const data = await scanApi.getGraph(parseInt(scanId));
        setGraphData(data);
        setNodes(data.nodes);
        setEdges(data.edges);
      } catch (error) {
        toast.error(handleApiError(error));
      } finally {
        setLoading(false);
      }
    };
    loadGraph();
  }, [scanId, setNodes, setEdges]);

  const onNodeClick = useCallback(async (_: any, node: Node) => {
    setSelectedNode(node);
    
    // Check if there is a conflict unit for this node in the scan's conflicts
    try {
      setLoadingRag(true);
      const conflicts = await scanApi.getConflicts(parseInt(scanId!));
      const conflict = conflicts.find((c: any) => c.file_path === node.data.filePath);
      
      if (conflict && conflict.unit_id) {
        const rag = await scanApi.ragInspect(parseInt(scanId!), conflict.unit_id);
        setRagData(rag);
      } else {
        setRagData(null);
      }
    } catch (e) {
      console.error(e);
      setRagData(null);
    } finally {
      setLoadingRag(false);
    }
  }, [scanId]);

  if (loading) {
    return (
      <div className="ambient-bg min-h-screen">
        <Header title={`Knowledge Graph`} />
        <div className="flex items-center justify-center h-[80vh]">
          <LoadingSpinner message="Loading AST Graph..." />
        </div>
      </div>
    );
  }

  return (
    <div className="ambient-bg min-h-screen flex flex-col">
      <Header title={`Graph Explorer — Scan #${scanId}`} />
      
      {/* Top Metrics Bar */}
      <div className="pt-24 px-4 pb-4">
        <div className="flex items-center justify-between mb-4">
          <motion.button
            onClick={() => navigate(`/scans/${scanId}`)}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            whileHover={{ x: -4 }}
          >
            <ArrowLeft size={18} />
            Back to Scan
          </motion.button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="Total Nodes"
            value={graphData?.stats.total_nodes || 0}
            icon={<Box className="w-5 h-5" />}
            color="indigo"
          />
          <MetricCard
            label="Dependencies (Edges)"
            value={graphData?.stats.total_edges || 0}
            icon={<LinkIcon className="w-5 h-5" />}
            color="emerald"
          />
          <MetricCard
            label="File Summaries"
            value={graphData?.stats.total_file_summaries || 0}
            icon={<FileText className="w-5 h-5" />}
            color="amber"
          />
          <MetricCard
            label="RAG Readiness"
            value="100%"
            icon={<Database className="w-5 h-5" />}
            color="cyan"
          />
        </div>
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex gap-4 px-4 pb-4 h-[calc(100vh-220px)]">
        
        {/* Left Sidebar: File Summaries */}
        <div className="w-1/4 h-full flex flex-col gap-4">
          <GlassCard className="flex-1 p-4 flex flex-col overflow-hidden">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <FileText size={18} className="text-indigo-400" />
              File Summaries
            </h3>
            <div className="overflow-y-auto space-y-3 flex-1 pr-2">
              {graphData?.file_summaries.map((fs: any, i: number) => (
                <div key={i} className="p-3 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-colors">
                  <p className="text-sm font-mono text-indigo-300 break-all mb-2">{fs.file_path}</p>
                  <p className="text-xs text-white/60 mb-2 line-clamp-3">{fs.summary_text}</p>
                  <div className="flex gap-3 text-xs text-white/40">
                    <span>Symbols: {fs.symbol_count}</span>
                    <span>Imports: {fs.import_count}</span>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>

        {/* Center: React Flow Canvas */}
        <div className="w-2/4 h-full rounded-2xl overflow-hidden border border-white/10 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            className="bg-black/40"
          >
            <Background color="#ffffff" gap={16} size={1} />
            <Controls className="bg-black/50 border-white/10 fill-white" />
            <MiniMap className="bg-black/80 border border-white/10" maskColor="rgba(0,0,0,0.5)" />
          </ReactFlow>
        </div>

        {/* Right Sidebar: Node & RAG Inspector */}
        <div className="w-1/4 h-full flex flex-col gap-4">
          <GlassCard className="flex-1 p-4 flex flex-col overflow-hidden">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Activity size={18} className="text-emerald-400" />
              Live RAG Inspector
            </h3>
            
            {!selectedNode ? (
              <div className="flex-1 flex items-center justify-center text-center p-6 text-white/40">
                <p>Click a node in the graph to inspect its RAG context bundle.</p>
              </div>
            ) : loadingRag ? (
              <div className="flex-1 flex items-center justify-center">
                <LoadingSpinner size="sm" message="Building Context Bundle..." />
              </div>
            ) : !ragData ? (
              <div className="flex-1 p-4 text-center">
                <AlertCircle className="w-8 h-8 text-amber-500/50 mx-auto mb-2" />
                <p className="text-white/60 text-sm">No conflict unit exists for this specific symbol yet.</p>
                <div className="mt-6 p-4 bg-white/5 rounded-lg text-left">
                  <p className="text-xs font-bold text-white/50 mb-1">NODE DETAILS</p>
                  <p className="text-sm font-mono text-indigo-300 break-all">{selectedNode.data.label}</p>
                  <p className="text-xs text-white/70 mt-1">{selectedNode.data.filePath}</p>
                </div>
              </div>
            ) : (
              <div className="overflow-y-auto space-y-4 flex-1 pr-2">
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-bold text-emerald-400">CONTEXT BUNDLE BUILT</span>
                    <span className="text-xs font-mono text-emerald-300">{ragData.token_estimate} / {ragData.token_budget_max} tokens</span>
                  </div>
                  <div className="w-full bg-black/40 rounded-full h-1.5 mb-2">
                    <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${ragData.token_utilization_pct}%` }}></div>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-bold text-white/50 mb-2">TOKEN BREAKDOWN</p>
                  {Object.entries(ragData.token_breakdown).map(([key, count]: any) => (
                    count > 0 && (
                      <div key={key} className="flex justify-between text-xs mb-1">
                        <span className="text-white/70">{key.replace('_', ' ')}</span>
                        <span className="text-white/90 font-mono">{count}</span>
                      </div>
                    )
                  ))}
                </div>

                <div className="pt-4 border-t border-white/10">
                  <p className="text-xs font-bold text-white/50 mb-2">DEPENDENCY CONTEXT</p>
                  <div className="space-y-2">
                    <div className="p-2 bg-white/5 rounded">
                      <span className="text-[10px] text-white/40 block">CALLERS ({ragData.callers.length})</span>
                      <p className="text-xs text-white/80 font-mono break-all">{ragData.callers.join(', ') || 'none'}</p>
                    </div>
                    <div className="p-2 bg-white/5 rounded">
                      <span className="text-[10px] text-white/40 block">CALLEES ({ragData.callees.length})</span>
                      <p className="text-xs text-white/80 font-mono break-all">{ragData.callees.join(', ') || 'none'}</p>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-white/10">
                  <p className="text-xs font-bold text-white/50 mb-2">RETRIEVED FILE SUMMARY</p>
                  <p className="text-xs text-white/70 italic p-3 bg-white/5 rounded-lg border-l-2 border-indigo-500">
                    "{ragData.file_summary}"
                  </p>
                </div>
              </div>
            )}
          </GlassCard>
        </div>

      </div>
    </div>
  );
}
