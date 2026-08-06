import axios, { isAxiosError } from 'axios';
import { supabase } from '@/services/supabaseClient';

/** Default for CRUD / auth / list calls. */
const DEFAULT_TIMEOUT_MS = 15_000;

/**
 * AI / Intake pipelines that can run for minutes (OCR, NER, risk, knowledge
 * graph, Diagnosis, Research, Prescription, Medical Report). The default
 * 15s CRUD timeout is far too short for these.
 */
export const AI_AGENT_TIMEOUT_MS = 10 * 60 * 1000;

/** Pull a human-readable message out of an Axios / Error rejection. */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message)) {
      return (
        'Request timed out — Intake and AI Agent steps can take a few minutes ' +
        'while the backend finishes. The work may still complete in the background; ' +
        'refresh the page or retry. Check /ai/orchestrator if this keeps happening.'
      );
    }
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg || JSON.stringify(item)).join(', ');
    }
    if (error.message) return error.message;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: DEFAULT_TIMEOUT_MS,
});

apiClient.interceptors.request.use(
  async (config) => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const isLoginRequest = error.config?.url?.includes('/auth/login');
      if (!isLoginRequest) {
        await supabase.auth.signOut();
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
