"""Dataset-grounded validation for Emergency Agent using HLT-005 synthetic admissions."""
from __future__ import annotations
import argparse, csv, json, math, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))

from app.ai.emergency.alert_generator import EmergencyAlertGenerator
from app.ai.emergency.critical_event_detector import CriticalEventDetector
from app.ai.emergency.icu_predictor import ICURequirementPredictor
from app.ai.emergency.priority_ranker import PatientPriorityRanker
from app.ai.emergency.triage_classifier import EmergencyTriageClassifier
from app.ai.emergency.vital_monitor import VitalMonitor

def macro_f1(true,pred):
    labels=sorted(set(true)|set(pred)); vals=[]
    for label in labels:
        tp=sum(t==label and p==label for t,p in zip(true,pred)); fp=sum(t!=label and p==label for t,p in zip(true,pred)); fn=sum(t==label and p!=label for t,p in zip(true,pred))
        pr=tp/(tp+fp) if tp+fp else 0.0; rc=tp/(tp+fn) if tp+fn else 0.0
        vals.append(2*pr*rc/(pr+rc) if pr+rc else 0.0)
    return sum(vals)/len(vals) if vals else 0.0

def binary_metrics(true,pred):
    tp=sum(t and p for t,p in zip(true,pred)); tn=sum((not t) and (not p) for t,p in zip(true,pred)); fp=sum((not t) and p for t,p in zip(true,pred)); fn=sum(t and (not p) for t,p in zip(true,pred))
    acc=(tp+tn)/len(true) if true else 0.0; pr=tp/(tp+fp) if tp+fp else 0.0; rc=tp/(tp+fn) if tp+fn else 0.0; f1=2*pr*rc/(pr+rc) if pr+rc else 0.0
    return {'accuracy':acc,'precision':pr,'recall':rc,'f1_score':f1}

def triage_label(esi):
    return {1:'Critical',2:'Critical',3:'Urgent',4:'Semi-Urgent',5:'Routine'}[int(esi)]

def vital_rows(row):
    rows=[]
    if row.get('triage_hr'): rows.append({'name':'Heart Rate','value':row['triage_hr'],'unit':'bpm'})
    if row.get('triage_spo2'): rows.append({'name':'SpO2','value':row['triage_spo2'],'unit':'%'})
    if row.get('triage_sbp') and row.get('triage_dbp'): rows.append({'name':'Blood Pressure','value':f"{row['triage_sbp']}/{row['triage_dbp']}",'unit':'mmHg'})
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--admissions',required=True); ap.add_argument('--max-cases',type=int,default=1000); ap.add_argument('--output',default='validation/results/dataset/emergency_hlt005')
    args=ap.parse_args(); src=Path(args.admissions); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    if not src.is_file(): raise SystemExit(f'Missing admissions file: {src}')
    monitor=VitalMonitor(); detector=CriticalEventDetector(); triage=EmergencyTriageClassifier(); icu=ICURequirementPredictor(); alerts=EmergencyAlertGenerator(); ranker=PatientPriorityRanker()
    rows=list(csv.DictReader(src.open(encoding='utf-8',newline=''))); rows=rows[:args.max_cases] if args.max_cases else rows
    tri_true=[]; tri_pred=[]; icu_true=[]; icu_pred=[]; pri_true=[]; pri_pred=[]; alert_true=[]; alert_pred=[]; cases=[]
    for row in rows:
        try: esi=int(float(row.get('esi_level','')))
        except (TypeError,ValueError): continue
        if esi not in {1,2,3,4,5}: continue
        monitoring=monitor.monitor(vital_rows(row))
        events=detector.detect(conditions=[],symptoms=[],monitoring=monitoring,risk_level=None,risk_alerts=[])
        tri=triage.classify(monitoring=monitoring,events=events,risk_score=None,risk_level=None)
        ic=icu.predict(monitoring=monitoring,events=events,risk_score=None,risk_level=None)
        al=alerts.generate(monitoring=monitoring,triage=tri,events=events,icu=ic)
        pr=ranker.rank(triage=tri,monitoring=monitoring,events=events,icu_signal=ic.signal)
        gt=triage_label(esi); ic_gt=int(row.get('icu_flag') or 0)==1; alert_gt=esi<=3
        tri_true.append(gt); tri_pred.append(tri.category); icu_true.append(ic_gt); icu_pred.append(ic.signal=='High'); pri_true.append(gt); pri_pred.append(pr.priority_level); alert_true.append(alert_gt); alert_pred.append(al.alert_count>0)
        cases.append({'case_id':str(row.get('admission_id') or row.get('patient_id')),'task_ids':['emergency_triage_classification','emergency_icu_requirement_prediction','emergency_patient_priority_ranking','emergency_alert_generation'],'input':{'esi_hidden':True,'vitals':vital_rows(row)},'ground_truth':{'triage':gt,'icu_required':ic_gt,'alert_expected':alert_gt,'priority_level':gt},'prediction':{'triage':tri.category,'icu_signal':ic.signal,'priority_level':pr.priority_level,'alert_generated':al.alert_count>0},'metrics':{'triage_match':tri.category==gt,'icu_match':(ic.signal=='High')==ic_gt,'priority_match':pr.priority_level==gt,'alert_match':(al.alert_count>0)==alert_gt}})
    task_summaries={
      'emergency_triage_classification':{'accuracy':sum(a==b for a,b in zip(tri_true,tri_pred))/len(tri_true),'macro_f1':macro_f1(tri_true,tri_pred)},
      'emergency_icu_requirement_prediction':binary_metrics(icu_true,icu_pred),
      'emergency_patient_priority_ranking':{'accuracy':sum(a==b for a,b in zip(pri_true,pri_pred))/len(pri_true),'macro_f1':macro_f1(pri_true,pri_pred)},
      'emergency_alert_generation':binary_metrics(alert_true,alert_pred),
    }
    with (out/'cases.jsonl').open('w',encoding='utf-8') as f:
        for case in cases: f.write(json.dumps(case)+'\n')
    for task_id,metrics in task_summaries.items():
        taskdir=out/task_id; taskdir.mkdir(parents=True,exist_ok=True); payload={'task_id':task_id,'dataset':'HLT-005 Synthetic Hospital Admission Dataset','cases_evaluated':len(cases),'metrics':metrics,'clinical_accuracy_claim':False}
        payload.update(metrics); (taskdir/'cases.jsonl').write_text((out/'cases.jsonl').read_text(encoding='utf-8'),encoding='utf-8'); (taskdir/'summary.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    unsupported={'emergency_vital_monitoring':{'status':'NOT_VALIDATABLE','reason':'No independent label; validated by deterministic rule-conformance tests.'},'emergency_critical_event_detection':{'status':'NOT_VALIDATABLE','reason':'HLT-005 does not provide independent event annotations.'}}
    summary={'dataset':'HLT-005 Synthetic Hospital Admission Dataset','cases_evaluated':len(cases),'task_summaries':task_summaries,'not_validatable':unsupported,'clinical_accuracy_claim':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8'); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()