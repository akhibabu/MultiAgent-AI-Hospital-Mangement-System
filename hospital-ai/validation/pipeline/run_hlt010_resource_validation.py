"""Dataset-grounded operational validation for Resource Allocation using HLT-010.

HLT-010 is fully synthetic. It contains daily hospital capacity, OR schedules,
staffing shifts and equipment utilization. It does not contain patient-to-resource
allocation labels. Therefore this runner evaluates availability-to-allocation
agreement for bed, ICU, ventilator and equipment resources, while explicitly
leaving specialist staff assignment and demand forecasting unscored.
"""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; BACKEND=ROOT/'backend'
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.ai.resource_allocation.availability_assessor import AvailabilityAssessor
from app.ai.resource_allocation.models import ResourceRequirement

def bin_metrics(true,pred):
    tp=sum(t==1 and p==1 for t,p in zip(true,pred)); tn=sum(t==0 and p==0 for t,p in zip(true,pred)); fp=sum(t==0 and p==1 for t,p in zip(true,pred)); fn=sum(t==1 and p==0 for t,p in zip(true,pred))
    acc=(tp+tn)/len(true) if true else 0.0; pr=tp/(tp+fp) if tp+fp else 0.0; rc=tp/(tp+fn) if tp+fn else 0.0; f1=2*pr*rc/(pr+rc) if pr+rc else 0.0
    return {'accuracy':acc,'precision':pr,'recall':rc,'f1_score':f1}

def read_csv(path): return list(csv.DictReader(Path(path).open(encoding='utf-8',newline='')))
def to_int(v):
    try: return int(float(v or 0))
    except (TypeError,ValueError): return 0

def score_rows(rows, task_id, resource_type_fn, qty_fn, available_fn, name_fn, limit):
    assessor=AvailabilityAssessor(); true=[]; pred=[]; cases=[]
    for row in rows[:limit] if limit else rows:
        quantity=max(0,qty_fn(row)); available=1 if available_fn(row) else 0
        # For allocation validation, the benchmark case asks for one unit whenever the row has capacity.
        req=ResourceRequirement(requirement=resource_type_fn(row),resource_type=resource_type_fn(row),required_quantity=1,source='HLT-010 benchmark',rationale='Availability derived from the operational dataset.',priority=50)
        inv=[{'id':str(row.get('asset_id') or row.get('facility_id') or row.get('record_date') or len(cases)),'resource_name':name_fn(row),'resource_type':resource_type_fn(row),'available_quantity':quantity,'status':'Available' if available else 'Unavailable'}]
        out=assessor.assess(requirements=[req],resources=inv,doctors=[])[0]; got=1 if out.allocated_quantity>0 else 0
        true.append(available); pred.append(got)
        cases.append({'case_id':str(row.get('asset_id') or f"{row.get('facility_id','FAC')}-{row.get('census_date',row.get('record_date','NA'))}-{len(cases):05d}"),'task_id':task_id,'status':'SCORED','prediction':{'status':out.status,'allocated_quantity':out.allocated_quantity},'ground_truth':{'available':bool(available),'available_quantity':quantity},'metrics':{'match':got==available}})
    return bin_metrics(true,pred),cases

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--hospital-resources',required=True); ap.add_argument('--equipment',required=True); ap.add_argument('--max-cases',type=int,default=500); ap.add_argument('--output',default='validation/results/dataset/resource_hlt010')
    a=ap.parse_args(); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    hr=read_csv(a.hospital_resources); eq=read_csv(a.equipment); results={}; all_cases=[]
    bed_metrics,bed_cases=score_rows(hr,'resource_allocation_bed_allocation',lambda r:'Bed',lambda r:max(to_int(r.get('total_beds'))-to_int(r.get('occupied_beds')),0),lambda r:to_int(r.get('total_beds'))>to_int(r.get('occupied_beds')),lambda r:f"Bed capacity {r.get('facility_id','facility')}",a.max_cases); results['resource_allocation_bed_allocation']=bed_metrics; all_cases.extend(bed_cases)
    icu_metrics,icu_cases=score_rows(hr,'resource_allocation_icu_allocation',lambda r:'ICU Bed',lambda r:max(to_int(r.get('icu_beds_x'))-to_int(r.get('icu_occupied')),0),lambda r:to_int(r.get('icu_beds_x'))>to_int(r.get('icu_occupied')),lambda r:f"ICU capacity {r.get('facility_id','facility')}",a.max_cases); results['resource_allocation_icu_allocation']=icu_metrics; all_cases.extend(icu_cases)
    vents=[r for r in eq if 'ventilator' in str(r.get('equipment_class') or '').lower()]; vent_metrics,vent_cases=score_rows(vents,'resource_allocation_ventilator_allocation',lambda r:'Ventilator',lambda r:1,lambda r:not bool(str(r.get('failure_flag') or '').lower() in {'true','1','yes'}) and to_int(r.get('downtime_hours'))==0,lambda r:str(r.get('asset_id')),a.max_cases); results['resource_allocation_ventilator_allocation']=vent_metrics; all_cases.extend(vent_cases)
    equip_metrics,equip_cases=score_rows(eq,'resource_allocation_equipment_allocation',lambda r:str(r.get('equipment_class') or 'Medical Equipment'),lambda r:1,lambda r:not bool(str(r.get('failure_flag') or '').lower() in {'true','1','yes'}) and to_int(r.get('downtime_hours'))==0,lambda r:str(r.get('asset_id')),a.max_cases); results['resource_allocation_equipment_allocation']=equip_metrics; all_cases.extend(equip_cases)
    with (out/'cases.jsonl').open('w',encoding='utf-8') as f:
        for c in all_cases: f.write(json.dumps(c)+'\n')
    for task_id,metrics in results.items():
        td=out/task_id; td.mkdir(parents=True,exist_ok=True); tc=[c for c in all_cases if c['task_id']==task_id]; (td/'cases.jsonl').write_text('\n'.join(json.dumps(c) for c in tc)+'\n',encoding='utf-8'); (td/'summary.json').write_text(json.dumps({'task_id':task_id,'dataset':'HLT-010 Synthetic Hospital Resource Usage Dataset','cases_evaluated':len(tc),'accuracy':metrics['accuracy'],'precision':metrics['precision'],'recall':metrics['recall'],'f1_score':metrics['f1_score'],'clinical_accuracy_claim':False,'note':'This benchmark measures agreement with dataset-recorded resource availability, not historical patient-to-resource assignment.'},indent=2)+'\n',encoding='utf-8')
    summary={'dataset':'HLT-010 Synthetic Hospital Resource Usage Dataset','task_summaries':results,'not_validatable':{'resource_allocation_staff_allocation':'No patient-specific staff assignment ground truth in HLT-010.','resource_allocation_demand_forecasting':'Demand forecasting is not implemented in the current Resource Allocation Agent.'},'clinical_accuracy_claim':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8'); print(json.dumps(summary,indent=2))

if __name__=='__main__': main()