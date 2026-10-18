import axios, { AxiosError } from 'axios';
import {
  HealthResponse,
  DataSourcesResponse,
  CaseCreatePayload,
  CaseItem,
  GraphDataResponse,
  EvidenceItem,
  TimelineEvent,
  InvestigationReportResponse,
  AnalyzeCaseResponse,
  TraceChainBlock,
  TraceChainVerifyResponse,
  MLStatusResponse,
  MLPredictRequest,
  MLPredictResponse,
  LiveStatusResponse,
  SimulateEventRequest,
  CaseLeadsResponse,
  MatricesResponse,
  ExposureResponse,
  CashoutForecastResponse,
  DemoTamperResponse,
  DemoResetResponse,
} from '@/types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export function parseApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<{ detail?: string | Array<{ msg: string }> }>;
    if (err.response?.data) {
      const detail = err.response.data.detail;
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ');
    }
    if (err.message === 'Network Error') {
      return 'Unable to connect to GhostTrace backend at ' + API_BASE + '. Please verify the backend is running.';
    }
    return err.message;
  }
  return String(error);
}

// ----------------- Core API Endpoints -----------------

export const api = {
  // Health
  getHealth: async (): Promise<HealthResponse> => {
    const res = await apiClient.get<HealthResponse>('/api/health');
    return res.data;
  },

  // Data Sources
  getDataSources: async (): Promise<DataSourcesResponse> => {
    const res = await apiClient.get<DataSourcesResponse>('/api/data-sources');
    return res.data;
  },

  // Cases
  listCases: async (): Promise<CaseItem[]> => {
    const res = await apiClient.get<CaseItem[]>('/api/cases');
    return res.data;
  },

  getCase: async (caseId: string): Promise<CaseItem> => {
    const res = await apiClient.get<CaseItem>(`/api/cases/${caseId}`);
    return res.data;
  },

  createCase: async (payload: CaseCreatePayload): Promise<CaseItem> => {
    const res = await apiClient.post<CaseItem>('/api/cases', payload);
    return res.data;
  },

  analyzeCase: async (caseId: string): Promise<AnalyzeCaseResponse> => {
    const res = await apiClient.post<AnalyzeCaseResponse>(`/api/cases/${caseId}/analyze`);
    return res.data;
  },

  getCaseGraph: async (caseId: string): Promise<GraphDataResponse> => {
    const res = await apiClient.get<GraphDataResponse>(`/api/cases/${caseId}/graph`);
    return res.data;
  },

  getCaseEvidence: async (caseId: string): Promise<EvidenceItem[]> => {
    const res = await apiClient.get<EvidenceItem[]>(`/api/cases/${caseId}/evidence`);
    return res.data;
  },

  getCaseTimeline: async (caseId: string): Promise<TimelineEvent[]> => {
    const res = await apiClient.get<TimelineEvent[]>(`/api/cases/${caseId}/timeline`);
    return res.data;
  },

  getCaseReport: async (caseId: string): Promise<InvestigationReportResponse> => {
    const res = await apiClient.get<InvestigationReportResponse>(`/api/cases/${caseId}/report`);
    return res.data;
  },

  getCaseLeads: async (caseId: string): Promise<CaseLeadsResponse> => {
    const res = await apiClient.get<CaseLeadsResponse>(`/api/cases/${caseId}/leads`);
    return res.data;
  },

  getCaseMatrices: async (caseId: string): Promise<MatricesResponse> => {
    const res = await apiClient.get<MatricesResponse>(`/api/cases/${caseId}/matrices`);
    return res.data;
  },

  getCaseExposure: async (caseId: string): Promise<ExposureResponse> => {
    const res = await apiClient.get<ExposureResponse>(`/api/cases/${caseId}/exposure`);
    return res.data;
  },

  getCashoutForecast: async (caseId: string): Promise<CashoutForecastResponse> => {
    const res = await apiClient.get<CashoutForecastResponse>(`/api/cases/${caseId}/cashout-forecast`);
    return res.data;
  },

  // TraceChain
  getBlocks: async (): Promise<TraceChainBlock[]> => {
    const res = await apiClient.get<TraceChainBlock[]>('/api/chain/blocks');
    return res.data;
  },

  verifyChain: async (): Promise<TraceChainVerifyResponse> => {
    const res = await apiClient.get<TraceChainVerifyResponse>('/api/chain/verify');
    return res.data;
  },

  demoTamper: async (): Promise<DemoTamperResponse> => {
    const res = await apiClient.post<DemoTamperResponse>('/api/chain/demo-tamper');
    return res.data;
  },

  demoReset: async (): Promise<DemoResetResponse> => {
    const res = await apiClient.post<DemoResetResponse>('/api/chain/demo-reset');
    return res.data;
  },

  verifyDemoChain: async (): Promise<TraceChainVerifyResponse> => {
    const res = await apiClient.get<TraceChainVerifyResponse>('/api/chain/demo-verify');
    return res.data;
  },

  // Machine Learning
  getMLStatus: async (): Promise<MLStatusResponse> => {
    const res = await apiClient.get<MLStatusResponse>('/api/ml/status');
    return res.data;
  },

  predictTransaction: async (payload: MLPredictRequest): Promise<MLPredictResponse> => {
    const res = await apiClient.post<MLPredictResponse>('/api/ml/predict', payload);
    return res.data;
  },

  trainModel: async (payload: { dataset_name?: string; max_rows?: number }) => {
    const res = await apiClient.post('/api/ml/train', payload);
    return res.data;
  },

  // Real-Time & Live Ingestion
  getLiveStatus: async (): Promise<LiveStatusResponse> => {
    const res = await apiClient.get<LiveStatusResponse>('/api/live/status');
    return res.data;
  },

  simulateLiveEvent: async (payload: SimulateEventRequest = {}): Promise<any> => {
    const res = await apiClient.post('/api/live/simulate-event', payload);
    return res.data;
  },

  triggerOSINTCollection: async (): Promise<any> => {
    const res = await apiClient.post('/api/live/osint/collect');
    return res.data;
  },
};
