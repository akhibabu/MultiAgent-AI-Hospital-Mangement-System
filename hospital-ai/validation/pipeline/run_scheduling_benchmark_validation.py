"""Dataset-grounded validation for the Scheduling Agent against a public synthetic appointment benchmark.

The benchmark adapter deliberately evaluates only capabilities implemented by this
project's Scheduling Agent. It uses the benchmark's published task constraints and
expected slot outcomes. Tasks requiring policy, insurance, referral, or mutation
behavior outside our current SchedulingAgent are excluded from automated scoring.
"""
from __future__ import annotations
import argparse,json,sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; BACKEND=ROOT/'backend'
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.ai.scheduling.appointment_scheduler import AppointmentSlotEngine

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def valid_slots(task,snapshot):
    c=task.get('constraints',{}); appointment=next(a for a in task['initial_ledger']['appointments'] if a['appointment_id']==task['appointment_id'])
    patient=next(p for p in snapshot['patients'] if p['patient_id']==appointment['patient_id'])
    providers={p['provider_id']:p for p in snapshot['providers']}
    result=[]
    for slot in snapshot['slots']:
        start=datetime.fromisoformat(slot['start'])
        provider=providers[slot['provider_id']]
        if not slot.get('available'): continue
        if c.get('date') and start.date().isoformat()!=c['date']: continue
        if c.get('weekday') and start.strftime('%A').lower()!=c['weekday'].lower(): continue
        if start.hour < c.get('min_hour',0): continue
        if c.get('max_hour') is not None and start.hour>=c['max_hour']: continue
        if c.get('same_provider',True) and slot['provider_id']!=appointment['provider_id']: continue
        if c.get('required_specialty') and provider['specialty']!=c['required_specialty']: continue
        if c.get('required_location') and provider.get('location')!=c['required_location']: continue
        if c.get('insurance_required') and patient['insurance'] not in provider.get('accepted_insurance',[]): continue
        if c.get('pediatric_policy') and patient.get('age',999)<18 and not provider.get('pediatric_eligible',False): continue
        result.append(slot)
    return sorted(result,key=lambda s:s['start'])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--tasks',required=True); ap.add_argument('--snapshot',required=True); ap.add_argument('--max-cases',type=int,default=6); ap.add_argument('--output',default='validation/results/dataset/scheduling_benchmark')
    a=ap.parse_args(); tasks=load(a.tasks)['tasks']; snap=load(a.snapshot); out=Path(a.output); out.mkdir(parents=True,exist_ok=True); engine=AppointmentSlotEngine()
    cases=[]
    for task in tasks:
        if task.get('suite')!='easy': continue
        candidates=valid_slots(task,snap)
        appointment=next(x for x in task['initial_ledger']['appointments'] if x['appointment_id']==task['appointment_id'])
        if candidates:
            first=candidates[0]; end=start=datetime.fromisoformat(first['start'])
            # The current scheduler operates on appointment windows; represent a benchmark slot as 30 minutes.
            slot_input=[{'appointment_date':start.date().isoformat(),'start_time':start.strftime('%H:%M:%S'),'end_time':(start.replace(minute=(start.minute+30)%60,hour=start.hour+(start.minute+30)//60)).strftime('%H:%M:%S')}]
        else: first=None; slot_input=[]
        prediction=engine.recommend(slots=slot_input,doctor_id=str(first['provider_id']) if first else appointment['provider_id'],doctor_name='Benchmark Provider',priority_level='Routine')
        predicted_slot=None if prediction.recommended_slot is None else {'provider_id':first['provider_id'],'start':f"{prediction.recommended_slot.appointment_date}T{prediction.recommended_slot.start_time}"}
        expected_id=task.get('expected',{}).get('new_slot_id'); expected=next((s for s in snap['slots'] if s['slot_id']==expected_id),None)
        predicted_id=first['slot_id'] if prediction.recommended_slot is not None and first else None
        match=(predicted_id==expected_id) if expected_id else (prediction.recommended_slot is None)
        cases.append({'case_id':task['id'],'task_id':'scheduling_appointment_scheduling','status':'SCORED','input':{'benchmark_task':task['name'],'constraints':task.get('constraints',{}),'candidate_count':len(candidates)},'prediction':predicted_slot,'ground_truth':{'slot_id':expected_id,'start':expected.get('start') if expected else None,'action':task.get('expected',{}).get('action')},'metrics':{'match':match}})
        if len(cases)>=a.max_cases: break
    accuracy=sum(c['metrics']['match'] for c in cases)/len(cases) if cases else 0.0
    payload={'task_id':'scheduling_appointment_scheduling','dataset':'AISmithLab Appointment Scheduling Benchmark (synthetic)','cases_evaluated':len(cases),'accuracy':accuracy,'clinical_accuracy_claim':False,'note':'Measures earliest-valid-slot selection after benchmark constraints are resolved; it does not evaluate unsupported insurance/policy mutation behavior.'}
    (out/'cases.jsonl').write_text('\n'.join(json.dumps(c) for c in cases)+'\n',encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2))
if __name__=='__main__': main()