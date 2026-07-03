import axios, { AxiosError, AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Error handling
export const handleApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    if (axiosError.response?.status === 429) {
      return 'Rate limited. Please try again in a moment.';
    }
    if (axiosError.response?.status === 404) {
      return 'Resource not found.';
    }
    if (axiosError.response?.status === 500) {
      return 'Server error. Please try again later.';
    }
    if (axiosError.code === 'ECONNABORTED') {
      return 'Request timeout. Please check your connection.';
    }
    return axiosError.message || 'An error occurred';
  }
  return 'An unexpected error occurred';
};

// ── Repository Scan Endpoints ──────────────────────────────────────────────
export const scanApi = {
  // FIX: was /repos/scans/start with wrong field names
  startScan: async (upstreamUrl: string, forkUrl: string) => {
    const response = await api.post('/scan/start', {
      upstream_repo_url: upstreamUrl,
      fork_repo_url: forkUrl,
    });
    return response.data;
  },

  listScans: async () => {
    const response = await api.get('/scans');
    return response.data;
  },

  getScanStatus: async (scanId: number) => {
    const response = await api.get(`/scan/${scanId}`);
    return response.data;
  },

  // FIX: was /scans/{id}/metrics — backend has /scan/{id}/summary
  getScanSummary: async (scanId: number) => {
    const response = await api.get(`/scan/${scanId}/summary`);
    return response.data;
  },

  // FIX: was /scans/{id}/reconciliation_units — backend has /scan/{id}/conflicts
  getConflicts: async (scanId: number) => {
    const response = await api.get(`/scan/${scanId}/conflicts`);
    return response.data;
  },

  // NEW: graph data for react-flow visualization
  getGraph: async (scanId: number) => {
    const response = await api.get(`/scan/${scanId}/graph`);
    return response.data;
  },

  // NEW: live RAG inspector for a specific conflict unit
  ragInspect: async (scanId: number, unitId: number) => {
    const response = await api.get(`/scan/${scanId}/rag-inspect/${unitId}`);
    return response.data;
  },
};

// ── Debate Endpoints ───────────────────────────────────────────────────────
export const debateApi = {
  startDebate: async (unitId: number) => {
    const response = await api.post(`/debates/start?unit_id=${unitId}`);
    return response.data;
  },

  getDebateStatus: async (debateId: number) => {
    const response = await api.get(`/debates/${debateId}`);
    return response.data;
  },

  getDebateRounds: async (debateId: number) => {
    const response = await api.get(`/debates/${debateId}/rounds`);
    return response.data;
  },

  getDebateMetrics: async (debateId: number) => {
    const response = await api.get(`/debates/${debateId}/metrics`);
    return response.data;
  },

  getDebateConsensus: async (debateId: number) => {
    const response = await api.get(`/debates/${debateId}/consensus`);
    return response.data;
  },
};

export default api;
