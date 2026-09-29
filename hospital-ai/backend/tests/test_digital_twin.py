from app.ai.digital_twin.models import DigitalTwinScenario, HospitalTwinState, ResourceTwinState, StaffTwinState, FlowTwinState
from app.ai.digital_twin.simulator import DigitalTwinSimulator


def state():
    return HospitalTwinState(
        resources=[
            ResourceTwinState(resource_type="Bed", total_quantity=100, available_quantity=20, in_use_quantity=80, maintenance_quantity=0, out_of_service_quantity=0, utilization_percent=80),
            ResourceTwinState(resource_type="ICU Bed", total_quantity=10, available_quantity=2, in_use_quantity=8, maintenance_quantity=0, out_of_service_quantity=0, utilization_percent=80),
            ResourceTwinState(resource_type="Ventilator", total_quantity=10, available_quantity=5, in_use_quantity=5, maintenance_quantity=0, out_of_service_quantity=0, utilization_percent=50),
        ],
        staff=StaffTwinState(total_doctors=20, available_doctors=12, busy_doctors=6, on_leave_doctors=2, utilization_percent=40),
        flow=FlowTwinState(appointments_next_24h=10, appointments_next_7d=40, emergency_results_last_24h=2, high_or_critical_emergencies=1, icu_signals_last_24h=1, scheduling_runs_last_24h=3, allocation_runs_last_24h=2, allocation_conflicts_last_24h=1),
        operational_pressure=80,
        source_status={"resources": True},
        source_timestamps={},
    )


def test_simulation_projects_bed_and_icu_pressure():
    result = DigitalTwinSimulator().run(state(), DigitalTwinScenario(emergency_arrivals=8, planned_admissions=5, icu_admissions=2, ventilator_demand=3))
    beds = next(x for x in result.resource_projections if x.resource_type == "Bed")
    icu = next(x for x in result.resource_projections if x.resource_type == "ICU Bed")
    assert beds.projected_available == 7
    assert beds.projected_utilization_percent == 93.0
    assert icu.projected_available == 0
    assert icu.shortage == 0
    assert icu.status == "Critical"
    assert any(signal.target_agent == "resource_allocation" for signal in result.feedback_signals)
    assert any(signal.target_agent == "emergency" for signal in result.feedback_signals)


def test_simulation_includes_discharges_and_staff_absence():
    result = DigitalTwinSimulator().run(state(), DigitalTwinScenario(expected_discharges=10, icu_discharges=1, staff_absent=20))
    beds = next(x for x in result.resource_projections if x.resource_type == "Bed")
    assert beds.projected_available == 30
    bed_signal = next(b for b in result.bottlenecks if b.resource_type == "Bed")
    assert bed_signal.projected_utilization_percent == 70.0
    assert bed_signal.severity == "High"
    staff = next(b for b in result.bottlenecks if b.resource_type == "Clinical Staff")
    assert staff.shortage == 8
