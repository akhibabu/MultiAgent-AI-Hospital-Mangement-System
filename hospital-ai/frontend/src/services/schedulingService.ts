import apiClient,{AI_AGENT_TIMEOUT_MS} from '@/services/apiClient';
import type { SchedulingResult,SchedulingStartResult } from '@/types/scheduling';

export interface SchedulingRequest { patient_id:string; preferred_date:string; }

export const schedulingService={
  async start(payload:SchedulingRequest):Promise<SchedulingStartResult>{
    const {data}=await apiClient.post<SchedulingStartResult>('/ai/scheduling/start',payload,{timeout:AI_AGENT_TIMEOUT_MS});
    return data;
  },
  async result(patientId:string):Promise<SchedulingResult>{
    const {data}=await apiClient.get<SchedulingResult>('/ai/scheduling/'+patientId);
    return data;
  },
};
