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
    rows = [
        row
        for row in csv.DictReader(src.open(encoding="utf-8", newline=""))
        if str(row.get("esi_level") or "").strip() in {"1", "2", "3", "4", "5"}
    ]
    if args.max_cases:
        # Stratify by ESI so a small benchmark covers every acuity class.
        groups = {level: [] for level in (1, 2, 3, 4, 5)}
        for row in rows:
            groups[int(float(row["esi_level"]))].append(row)
        selected = []
        per_level = args.max_cases // 5
        remainder = args.max_cases % 5
        for level in (1, 2, 3, 4, 5):
            take = per_level + (1 if level <= remainder else 0)
            selected.extend(groups[level][:take])
        if len(selected) < args.max_cases:
            used = {str(r.get("admission_id") or r.get("patient_id")) for r in selected}
            for row in rows:
                key = str(row.get("admission_id") or row.get("patient_id"))
                if key not in used:
                    selected.append(row)
                    used.add(key)
                if len(selected) >= args.max_cases:
                    break
        rows = selected[:args.max_cases]
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
      'emergency_triage_classification':{'accuracy':sum(a==b for a,b in zip(tri_true,tri_pred))/len(tri_true),'macro_f1':macro_f1(tri_true,tri_pred),'headline_metric':'Accuracy','headline_value':sum(a==b for a,b in zip(tri_true,tri_pred))/len(tri_true)},
      'emergency_icu_requirement_prediction':{**binary_metrics(icu_true,icu_pred),'headline_metric':'F1','headline_value':binary_metrics(icu_true,icu_pred)['f1_score']},
      'emergency_patient_priority_ranking':{'accuracy':sum(a==b for a,b in zip(pri_true,pri_pred))/len(pri_true),'macro_f1':macro_f1(pri_true,pri_pred),'headline_metric':'Accuracy','headline_value':sum(a==b for a,b in zip(pri_true,pri_pred))/len(pri_true)},
      'emergency_alert_generation':{**binary_metrics(alert_true,alert_pred),'headline_metric':'F1','headline_value':binary_metrics(alert_true,alert_pred)['f1_score']},
    }
    with (out/'cases.jsonl').open('w',encoding='utf-8') as f:
        for case in cases: f.write(json.dumps(case) + chr(10))
    task_field_map = {
        'emergency_triage_classification': ('triage', 'triage_match', 'triage'),
        'emergency_icu_requirement_prediction': ('icu_required', 'icu_match', 'icu_signal'),
        'emergency_patient_priority_ranking': ('priority_level', 'priority_match', 'priority_level'),
        'emergency_alert_generation': ('alert_expected', 'alert_match', 'alert_generated'),
    }
    for task_id,metrics in task_summaries.items():
        taskdir=out/task_id; taskdir.mkdir(parents=True,exist_ok=True)
        truth_field, match_field, prediction_field = task_field_map[task_id]
        task_cases=[]
        for case in cases:
            task_cases.append({
                'case_id':case['case_id'],
                'task_id':task_id,
                'status':'SCORED',
                'input':case['input'],
                'prediction':case['prediction'].get(prediction_field),
                'ground_truth':case['ground_truth'].get(truth_field),
                'metrics':{'match':bool(case['metrics'][match_field])},
            })
        (taskdir/'cases.jsonl').write_text(chr(10).join(json.dumps(x) for x in task_cases) + chr(10), encoding='utf-8')
        payload={'task_id':task_id,'dataset':'HLT-005 Synthetic Hospital Admission Dataset','cases_evaluated':len(task_cases),'metrics':metrics,'clinical_accuracy_claim':False}
        payload.update(metrics)
        (taskdir/'summary.json').write_text(json.dumps(payload, indent=2) + chr(10), encoding='utf-8')
    unsupported={'emergency_vital_monitoring':{'status':'NOT_VALIDATABLE','reason':'No independent ground-truth label for threshold correctness.'},'emergency_critical_event_detection':{'status':'NOT_VALIDATABLE','reason':'HLT-005 does not provide independent event annotations.'}}
    summary={'dataset':'HLT-005 Synthetic Hospital Admission Dataset','cases_evaluated':len(cases), 'sampling':'ESI-stratified benchmark sample','task_summaries':task_summaries,'not_validatable':unsupported,'clinical_accuracy_claim':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8'); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()