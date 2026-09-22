"""Data access for the Scheduling Agent."""
from __future__ import annotations
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List
from uuid import UUID
from app.repositories.intake_repositories import SupabaseRestRepository

ACTIVE_STATUSES={"Scheduled","Rescheduled"}

class SchedulingDataRepository(SupabaseRestRepository):
    def __init__(self)->None:
        super().__init__("appointments")

    def list_doctors(self)->List[Dict[str,Any]]:
        rows=self._table_select("doctors",[
            ("select","id,doctor_number,first_name,last_name,specialization,department_id,availability_status,experience_years"),
            ("order","last_name.asc,first_name.asc")])
        return rows

    def list_departments(self)->Dict[str,str]:
        rows=self._table_select("departments",[("select","id,name")])
        return {str(r["id"]):str(r.get("name") or "") for r in rows if isinstance(r,dict) and r.get("id")}

    def list_availability(self, doctor_id: UUID)->List[Dict[str,Any]]:
        return self._table_select("doctor_availability",[
            ("select","id,doctor_id,day_of_week,start_time,end_time,slot_duration,is_available"),
            ("doctor_id",f"eq.{doctor_id}"),("is_available","eq.true"),
            ("order","day_of_week.asc,start_time.asc")])

    def list_active_appointments(self, *, start_date: date, end_date: date, doctor_id: UUID | None=None)->List[Dict[str,Any]]:
        params=[("select","id,patient_id,doctor_id,department_id,appointment_date,start_time,end_time,status,visit_type,reason_for_visit"),
                ("appointment_date",f"gte.{start_date.isoformat()}"),("appointment_date",f"lte.{end_date.isoformat()}"),
                ("status","in.(Scheduled,Rescheduled)"),("order","appointment_date.asc,start_time.asc")]
        if doctor_id: params.append(("doctor_id",f"eq.{doctor_id}"))
        return self._table_select("appointments",params)

    def patient_names(self, patient_ids: List[str])->Dict[str,str]:
        if not patient_ids: return {}
        rows=self._table_select("patients",[("select","id,first_name,last_name"),("id",f"in.({','.join(dict.fromkeys(patient_ids))})")])
        return {str(r["id"]):" ".join(filter(None,[r.get("first_name"),r.get("last_name")])) or "Patient" for r in rows if isinstance(r,dict) and r.get("id")}

    def latest_emergency_priorities(self, patient_ids: List[str])->Dict[str,Dict[str,Any]]:
        if not patient_ids: return {}
        rows=self._table_select("emergency_results",[("select","patient_id,patient_priority_json,created_at"),("patient_id",f"in.({','.join(dict.fromkeys(patient_ids))})"),("order","created_at.desc")])
        result={}
        for row in rows:
            pid=str(row.get("patient_id"));
            if pid and pid not in result: result[pid]=row.get("patient_priority_json") or {}
        return result

    def workload_counts(self, start_date: date, horizon_days: int=7)->Dict[str,int]:
        end=start_date+timedelta(days=max(0,horizon_days-1))
        rows=self.list_active_appointments(start_date=start_date,end_date=end)
        counts:Dict[str,int]={}
        for row in rows:
            did=str(row.get("doctor_id") or "")
            if did: counts[did]=counts.get(did,0)+1
        return counts

    def open_slots(self, doctor_id: UUID, start_date: date, horizon_days: int=14)->List[Dict[str,str]]:
        end_date=start_date+timedelta(days=max(0,horizon_days-1))
        availability=self.list_availability(doctor_id)
        bookings=self.list_active_appointments(start_date=start_date,end_date=end_date,doctor_id=doctor_id)
        result=[]
        for offset in range((end_date-start_date).days+1):
            d=start_date+timedelta(days=offset); day=d.weekday()
            for w in availability:
                if int(w.get("day_of_week",-1))!=day: continue
                ws=self._to_minutes(w.get("start_time")); we=self._to_minutes(w.get("end_time")); dur=max(5,int(w.get("slot_duration") or 30))
                cur=ws
                while cur+dur<=we:
                    s=self._minutes_to_time(cur); e=self._minutes_to_time(cur+dur)
                    if not any(self._overlap(s,e,self._parse_time(b.get("start_time")),self._parse_time(b.get("end_time"))) for b in bookings if str(b.get("appointment_date",""))[:10]==d.isoformat()):
                        result.append({"appointment_date":d.isoformat(),"start_time":s.strftime("%H:%M:%S"),"end_time":e.strftime("%H:%M:%S")})
                    cur+=dur
        return result

    def open_window(self, doctor_id: UUID, start_date: date, horizon_days: int, duration_minutes: int)->List[Dict[str,str]]:
        end_date=start_date+timedelta(days=max(0,horizon_days-1)); availability=self.list_availability(doctor_id)
        bookings=self.list_active_appointments(start_date=start_date,end_date=end_date,doctor_id=doctor_id)
        out=[]
        for offset in range((end_date-start_date).days+1):
            d=start_date+timedelta(days=offset); day=d.weekday()
            for w in availability:
                if int(w.get("day_of_week",-1))!=day: continue
                ws=self._to_minutes(w.get("start_time")); we=self._to_minutes(w.get("end_time")); cur=ws
                while cur+duration_minutes<=we:
                    s=self._minutes_to_time(cur); e=self._minutes_to_time(cur+duration_minutes)
                    if not any(self._overlap(s,e,self._parse_time(b.get("start_time")),self._parse_time(b.get("end_time"))) for b in bookings if str(b.get("appointment_date",""))[:10]==d.isoformat()):
                        out.append({"appointment_date":d.isoformat(),"start_time":s.strftime("%H:%M:%S"),"end_time":e.strftime("%H:%M:%S")}); return out
                    cur+=max(5,int(w.get("slot_duration") or 30))
        return out

    def _table_select(self, table:str, params:List[tuple[str,str]])->List[Dict[str,Any]]:
        old=self.table; self.table=table
        try: return self.select(params)
        finally: self.table=old

    @staticmethod
    def _to_minutes(value:Any)->int:
        t=SchedulingDataRepository._parse_time(value); return t.hour*60+t.minute
    @staticmethod
    def _parse_time(value:Any)->time:
        if isinstance(value,time): return value
        raw=str(value or "00:00:00"); return time.fromisoformat(raw if len(raw)>5 else raw+":00")
    @staticmethod
    def _minutes_to_time(minutes:int)->time: return time(hour=(minutes//60)%24,minute=minutes%60)
    @staticmethod
    def _overlap(sa:time,ea:time,sb:time,eb:time)->bool:
        am=sa.hour*60+sa.minute; ae=ea.hour*60+ea.minute; bm=sb.hour*60+sb.minute; be=eb.hour*60+eb.minute
        return am<be and bm<ae
