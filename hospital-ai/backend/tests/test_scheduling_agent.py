from datetime import date
from app.ai.scheduling.doctor_assignment import DoctorAssignmentEngine
from app.ai.scheduling.appointment_scheduler import AppointmentSlotEngine
from app.ai.scheduling.follow_up import FollowUpPlanner
from app.ai.scheduling.workload_balancer import WorkloadBalancer
from app.ai.scheduling.models import DoctorWorkload

def test_doctor_assignment_prefers_matching_available_doctor():
    result=DoctorAssignmentEngine().assign(doctors=[
      {"id":"1","first_name":"A","last_name":"Cardio","specialization":"Cardiology","availability_status":"Available","experience_years":10,"department_id":"d1"},
      {"id":"2","first_name":"B","last_name":"Gen","specialization":"General Medicine","availability_status":"Available","experience_years":15,"department_id":"d2"}],workload={"1":0,"2":0},department_names={"d1":"Cardiology","d2":"General"},preferred_doctor_id=None,requested_department_id=None,clinical_text="chest pain heart",emergency_level="Urgent",visit_type="Consultation")
    assert result.selected_doctor_id=="1"

def test_slot_engine_returns_earliest_recommendation():
    slots=[{"appointment_date":"2026-09-24","start_time":"09:00:00","end_time":"09:30:00"},{"appointment_date":"2026-09-24","start_time":"09:30:00","end_time":"10:00:00"}]
    result=AppointmentSlotEngine().recommend(slots=slots,doctor_id="1",doctor_name="Dr. Test",priority_level="Urgent")
    assert result.recommended_slot and result.recommended_slot.start_time=="09:00:00"

def test_follow_up_escalates_urgent_interval():
    result=FollowUpPlanner().plan(appointment_date=date(2026,9,24),interval_days=14,priority_level="Urgent")
    assert result.interval_days==7

def test_workload_balancer_finds_lower_load():
    result=WorkloadBalancer().balance(doctors=[DoctorWorkload(doctor_id="1",doctor_name="A",active_appointments=2,workload_score=28.6),DoctorWorkload(doctor_id="2",doctor_name="B",active_appointments=6,workload_score=85.7)])
    assert "A" in result.recommendation
