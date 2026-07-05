import React, { useState, useEffect, useCallback } from 'react';
import { Header } from '@/components/Header';
import { GlassCard } from '@/components/glass/GlassCard';
import { GlassBadge } from '@/components/glass/GlassBadge';
import { LoadingSpinner } from '@/components/glass/LoadingSpinner';
import { policyApi, handleApiError } from '@/lib/api';
import { toast } from 'sonner';
import { Shield, Upload, BookOpen, Trash2, ChevronRight, FileText, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Policy {
  id: number;
  name: string;
  description?: string;
  category: string;
  priority: string;
  version: string;
  status: string;
  file_name?: string;
  total_chunks: number;
  created_at: string;
}

interface PolicyChunk {
  chunk_index: number;
  chunk_text: string;
  token_count: number;
}

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

const CATEGORY_ICONS: Record<string, string> = {
  'Authentication': '🔐',
  'Authorization': '🛡️',
  'Security': '🔒',
  'Compliance': '📋',
  'Networking': '🌐',
  'Logging': '📊',
  'Infrastructure': '🏗️',
  'Architecture': '🏛️',
  'Performance': '⚡',
  'Database': '🗄️',
  'API Standards': '🔌',
  'Testing': '🧪',
  'Deployment': '🚀',
  'Coding Standards': '📝',
  'Enterprise Custom Rules': '⚙️',
};

export default function EnterpriseGovernance() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [selectedPolicyChunks, setSelectedPolicyChunks] = useState<PolicyChunk[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [activeTab, setActiveTab] = useState<'library' | 'upload' | 'explorer'>('library');

  const loadPolicies = useCallback(async () => {
    try {
      const data = await policyApi.listPolicies();
      setPolicies(data);
    } catch (e) {
      toast.error(handleApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPolicies(); }, [loadPolicies]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      toast.info(`Parsing and embedding "${file.name}"...`);
      const result = await policyApi.uploadPolicy(file);
      toast.success(`Policy "${result.name}" ingested — ${result.total_chunks} chunks embedded.`);
      await loadPolicies();
      setActiveTab('library');
    } catch (e) {
      toast.error(handleApiError(e));
    } finally {
      setUploading(false);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  const handleSelectPolicy = async (policy: Policy) => {
    setSelectedPolicy(policy);
    setChunksLoading(true);
    try {
      const data = await policyApi.getPolicyChunks(policy.id);
      setSelectedPolicyChunks(data.chunks || []);
    } catch {
      setSelectedPolicyChunks([]);
    } finally {
      setChunksLoading(false);
    }
    setActiveTab('explorer');
  };

  const handleDelete = async (policyId: number) => {
    try {
      await policyApi.deletePolicy(policyId);
      toast.success('Policy deleted.');
      if (selectedPolicy?.id === policyId) setSelectedPolicy(null);
      await loadPolicies();
    } catch (e) {
      toast.error(handleApiError(e));
    }
  };

  return (
    <div className="ambient-bg">
      <Header title="Enterprise Governance" />
      <main className="container mx-auto px-4 py-12 max-w-7xl">

        {/* Header Row */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/20">
              <Shield className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Enterprise Policy Library</h1>
              <p className="text-sm text-white/50">
                Upload policy documents to inject enterprise constraints into AI debates
              </p>
            </div>
          </div>
          <GlassBadge variant="medium">{policies.length} Policies Active</GlassBadge>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6">
          {(['library', 'upload', 'explorer'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize ${
                activeTab === tab
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              }`}
            >
              {tab === 'library' && <BookOpen className="w-4 h-4 inline mr-2" />}
              {tab === 'upload' && <Upload className="w-4 h-4 inline mr-2" />}
              {tab === 'explorer' && <FileText className="w-4 h-4 inline mr-2" />}
              {tab}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Policy Library Tab */}
          {activeTab === 'library' && (
            <motion.div key="library" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              {loading ? (
                <div className="flex justify-center py-20"><LoadingSpinner message="Loading policies..." /></div>
              ) : policies.length === 0 ? (
                <GlassCard className="p-12 text-center">
                  <Shield className="w-12 h-12 text-white/20 mx-auto mb-4" />
                  <p className="text-white/60 text-lg mb-2">No enterprise policies uploaded yet.</p>
                  <p className="text-white/40 text-sm mb-6">Upload policy documents to enable AI policy-aware conflict analysis.</p>
                  <button
                    onClick={() => setActiveTab('upload')}
                    className="px-4 py-2 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors text-sm"
                  >
                    Upload First Policy
                  </button>
                </GlassCard>
              ) : (
                <GlassCard className="overflow-hidden">
                  <table className="w-full">
                    <thead className="border-b border-white/10">
                      <tr className="text-xs text-white/50 uppercase tracking-wider">
                        <th className="text-left p-4">Policy</th>
                        <th className="text-left p-4">Category</th>
                        <th className="text-left p-4">Priority</th>
                        <th className="text-left p-4">Version</th>
                        <th className="text-left p-4">Chunks</th>
                        <th className="text-left p-4">Status</th>
                        <th className="text-left p-4">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {policies.map((policy, idx) => (
                        <motion.tr
                          key={policy.id}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.04 }}
                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                        >
                          <td className="p-4">
                            <div className="font-semibold text-white text-sm">{policy.name}</div>
                            {policy.file_name && <div className="text-xs text-white/40">{policy.file_name}</div>}
                          </td>
                          <td className="p-4">
                            <span className="text-sm text-white/70">
                              {CATEGORY_ICONS[policy.category] || '📄'} {policy.category}
                            </span>
                          </td>
                          <td className="p-4">
                            <GlassBadge variant={PRIORITY_COLORS[policy.priority] as any || 'medium'}>
                              {policy.priority}
                            </GlassBadge>
                          </td>
                          <td className="p-4 text-sm text-white/60">v{policy.version}</td>
                          <td className="p-4 text-sm text-white/60">{policy.total_chunks}</td>
                          <td className="p-4">
                            <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                              policy.status === 'active' ? 'bg-emerald-500/20 text-emerald-300' :
                              policy.status === 'draft' ? 'bg-amber-500/20 text-amber-300' :
                              'bg-white/10 text-white/40'
                            }`}>
                              {policy.status}
                            </span>
                          </td>
                          <td className="p-4">
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleSelectPolicy(policy)}
                                className="p-1.5 rounded-lg hover:bg-indigo-500/20 text-indigo-400 transition-colors"
                                title="Explore policy"
                              >
                                <ChevronRight className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDelete(policy.id)}
                                className="p-1.5 rounded-lg hover:bg-red-500/20 text-red-400 transition-colors"
                                title="Delete policy"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </GlassCard>
              )}
            </motion.div>
          )}

          {/* Upload Tab */}
          {activeTab === 'upload' && (
            <motion.div key="upload" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <GlassCard className="p-8">
                <h2 className="text-lg font-bold text-white mb-2">Upload Enterprise Policy Document</h2>
                <p className="text-sm text-white/50 mb-6">
                  Supports: <span className="text-indigo-300 font-mono">.md .txt .pdf .docx .json .yaml</span>
                  <br />The system will automatically parse, classify, chunk, and embed the document for AI retrieval.
                </p>

                {/* Drag & Drop Zone */}
                <label
                  htmlFor="policy-file-input"
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  className={`flex flex-col items-center justify-center w-full h-56 border-2 border-dashed rounded-2xl cursor-pointer transition-all ${
                    dragOver
                      ? 'border-indigo-400 bg-indigo-500/10'
                      : 'border-white/20 bg-white/5 hover:border-indigo-500/50 hover:bg-indigo-500/5'
                  }`}
                >
                  {uploading ? (
                    <div className="text-center">
                      <LoadingSpinner size="md" message="Parsing & embedding policy..." />
                      <p className="text-xs text-white/40 mt-3">This may take 15-30 seconds for large documents.</p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <Upload className="w-10 h-10 text-indigo-400/60 mx-auto mb-3" />
                      <p className="text-white/70 font-medium">Drag & drop your policy file here</p>
                      <p className="text-white/40 text-sm mt-1">or click to browse</p>
                    </div>
                  )}
                </label>
                <input
                  id="policy-file-input"
                  type="file"
                  accept=".md,.txt,.pdf,.docx,.json,.yaml,.yml"
                  onChange={handleFileInput}
                  className="hidden"
                  disabled={uploading}
                />

                {/* How it works */}
                <div className="mt-8 grid grid-cols-4 gap-4">
                  {[
                    { icon: <Upload className="w-4 h-4" />, label: 'Upload', desc: 'Drop your policy file' },
                    { icon: <FileText className="w-4 h-4" />, label: 'Parse & Classify', desc: 'Auto-detect category' },
                    { icon: <CheckCircle className="w-4 h-4" />, label: 'Embed', desc: 'Local AI embedding' },
                    { icon: <Shield className="w-4 h-4" />, label: 'Active', desc: 'Used in all debates' },
                  ].map((step, i) => (
                    <div key={i} className="text-center p-4 bg-white/5 rounded-xl">
                      <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 inline-flex mb-2">{step.icon}</div>
                      <p className="text-xs font-semibold text-white">{step.label}</p>
                      <p className="text-xs text-white/40 mt-1">{step.desc}</p>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </motion.div>
          )}

          {/* Policy Explorer Tab */}
          {activeTab === 'explorer' && (
            <motion.div key="explorer" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              {!selectedPolicy ? (
                <GlassCard className="p-12 text-center">
                  <BookOpen className="w-10 h-10 text-white/20 mx-auto mb-4" />
                  <p className="text-white/60">Select a policy from the Library tab to explore its contents.</p>
                </GlassCard>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Policy Metadata */}
                  <GlassCard className="p-6 lg:col-span-1">
                    <div className="text-2xl mb-3">{CATEGORY_ICONS[selectedPolicy.category] || '📄'}</div>
                    <h2 className="text-lg font-bold text-white mb-1">{selectedPolicy.name}</h2>
                    <p className="text-xs text-white/40 mb-4">{selectedPolicy.file_name}</p>
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-white/50">Category</span>
                        <span className="text-white/80">{selectedPolicy.category}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/50">Priority</span>
                        <GlassBadge variant={PRIORITY_COLORS[selectedPolicy.priority] as any || 'medium'}>
                          {selectedPolicy.priority}
                        </GlassBadge>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/50">Version</span>
                        <span className="text-white/80">v{selectedPolicy.version}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/50">Chunks</span>
                        <span className="text-indigo-300">{selectedPolicy.total_chunks} embedded</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/50">Status</span>
                        <span className="text-emerald-300 capitalize">{selectedPolicy.status}</span>
                      </div>
                    </div>
                  </GlassCard>

                  {/* Policy Chunks */}
                  <GlassCard className="p-6 lg:col-span-2 max-h-[600px] overflow-y-auto">
                    <h3 className="text-sm font-bold text-white/60 uppercase tracking-wider mb-4">
                      Embedded Chunks ({selectedPolicyChunks.length})
                    </h3>
                    {chunksLoading ? (
                      <LoadingSpinner message="Loading chunks..." />
                    ) : selectedPolicyChunks.length === 0 ? (
                      <p className="text-white/40 text-sm">No chunks found.</p>
                    ) : (
                      <div className="space-y-3">
                        {selectedPolicyChunks.map((chunk) => (
                          <div key={chunk.chunk_index} className="p-3 bg-white/5 rounded-lg border border-white/10">
                            <div className="flex justify-between items-center mb-2">
                              <span className="text-xs font-mono text-indigo-400">Chunk #{chunk.chunk_index}</span>
                              <span className="text-xs text-white/40">{chunk.token_count} tokens</span>
                            </div>
                            <p className="text-xs text-white/70 leading-relaxed">{chunk.chunk_text}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </GlassCard>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
