import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const startScan = async (upstreamUrl: string, forkUrl: string) => {
    const res = await axios.post(`${API_URL}/scan/start`, {
        upstream_repo_url: upstreamUrl,
        fork_repo_url: forkUrl
    });
    return res.data;
};

export const getScanStatus = async (scanId: number) => {
    const res = await axios.get(`${API_URL}/scan/${scanId}`);
    return res.data;
};

export const getScanSummary = async (scanId: number) => {
    const res = await axios.get(`${API_URL}/scan/${scanId}/summary`);
    return res.data;
};

export const getScanConflicts = async (scanId: number) => {
    const res = await axios.get(`${API_URL}/scan/${scanId}/conflicts`);
    return res.data;
};

export const startDebate = async (unitId: number) => {
    const res = await axios.post(`${API_URL}/debates/start?unit_id=${unitId}`);
    return res.data;
};
