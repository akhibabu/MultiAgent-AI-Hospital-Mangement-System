import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { getApiErrorMessage } from '@/services/apiClient';
import { schedulingService,type SchedulingRequest } from '@/services/schedulingService';
export const schedulingKeys={all:['scheduling'] as const,result:(patientId:string)=>['scheduling','result',patientId] as const};
export function useSchedulingResult(patientId:string|undefined){ return useQuery({queryKey:schedulingKeys.result(patientId||''),queryFn:()=>schedulingService.result(patientId!),enabled:Boolean(patientId),retry:false}); }
export function useStartScheduling(){ const qc=useQueryClient(); return useMutation({mutationFn:(payload:SchedulingRequest)=>schedulingService.start(payload),onSuccess:()=>{qc.invalidateQueries({queryKey:schedulingKeys.all});toast.success('Scheduling Agent completed — review the recommendations before booking.');},onError:(e)=>toast.error(getApiErrorMessage(e,'Scheduling Agent failed'))}); }
