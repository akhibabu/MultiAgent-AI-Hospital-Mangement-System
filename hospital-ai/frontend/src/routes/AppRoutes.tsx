import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from '@/components/common/ProtectedRoute';
import PublicOnlyRoute from '@/components/common/PublicOnlyRoute';
import MainLayout from '@/layouts/MainLayout';
import Loading from '@/components/ui/Loading';
import AICenterPage, {
  AIAgentPlaceholderPage,
} from '@/pages/AI/AICenterPage';

const LoginPage = lazy(() => import('@/pages/Login/LoginPage'));
const DashboardPage = lazy(() => import('@/pages/Dashboard/DashboardPage'));
const PatientsPage = lazy(() => import('@/pages/Patients/PatientsPage'));
const PatientProfilePage = lazy(
  () => import('@/pages/Patients/PatientProfilePage'),
);
const DoctorsPage = lazy(() => import('@/pages/Doctors/DoctorsPage'));
const DoctorProfilePage = lazy(
  () => import('@/pages/Doctors/DoctorProfilePage'),
);
const DepartmentsPage = lazy(
  () => import('@/pages/Departments/DepartmentsPage'),
);
const AvailabilityPage = lazy(
  () => import('@/pages/Availability/AvailabilityPage'),
);
const AppointmentsPage = lazy(
  () => import('@/pages/Appointments/AppointmentsPage'),
);
const AppointmentDetailPage = lazy(
  () => import('@/pages/Appointments/AppointmentDetailPage'),
);
const DoctorSchedulePage = lazy(
  () => import('@/pages/Appointments/DoctorSchedulePage'),
);
const MedicalRecordsPage = lazy(
  () => import('@/pages/MedicalRecords/MedicalRecordsPage'),
);
const MedicalRecordDetailPage = lazy(
  () => import('@/pages/MedicalRecords/MedicalRecordDetailPage'),
);
const DocumentViewerPage = lazy(
  () => import('@/pages/MedicalRecords/DocumentViewerPage'),
);
const ResourcesPage = lazy(() => import('@/pages/Resources/ResourcesPage'));
const AnnouncementsPage = lazy(
  () => import('@/pages/Announcements/AnnouncementsPage'),
);
const ProfilePage = lazy(() => import('@/pages/Profile/ProfilePage'));
const SettingsPage = lazy(() => import('@/pages/Settings/SettingsPage'));
const IntakeAgentPage = lazy(() => import('@/pages/AI/IntakeAgentPage'));
const DiagnosisAgentPage = lazy(() => import('@/pages/AI/DiagnosisAgentPage'));
const ResearchAgentPage = lazy(() => import('@/pages/AI/ResearchAgentPage'));
const PrescriptionAgentPage = lazy(
  () => import('@/pages/AI/PrescriptionAgentPage'),
);
const MedicalReportAgentPage = lazy(
  () => import('@/pages/AI/MedicalReportAgentPage'),
);
const AIOrchestratorPage = lazy(
  () => import('@/pages/AI/AIOrchestratorPage'),
);
const EmergencyAgentPage = lazy(
  () => import('@/pages/AI/EmergencyAgentPage'),
);
const ResourceAllocationAgentPage = lazy(
  () => import('@/pages/AI/ResourceAllocationAgentPage'),
);
const SchedulingAgentPage = lazy(
  () => import('@/pages/AI/SchedulingAgentPage'),
);
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));
const UnauthorizedPage = lazy(() => import('@/pages/UnauthorizedPage'));
const ServerErrorPage = lazy(() => import('@/pages/ServerErrorPage'));

function LazyFallback() {
  return <Loading message="Loading module…" />;
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<LazyFallback />}>
      <Routes>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>

        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="/server-error" element={<ServerErrorPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="patients" element={<PatientsPage />} />
            <Route path="patients/:patientId" element={<PatientProfilePage />} />
            <Route path="doctors" element={<DoctorsPage />} />
            <Route path="doctors/:doctorId" element={<DoctorProfilePage />} />
            <Route path="availability" element={<AvailabilityPage />} />
            <Route path="appointments" element={<AppointmentsPage />} />
            <Route
              path="appointments/schedule"
              element={<DoctorSchedulePage />}
            />
            <Route
              path="appointments/:appointmentId"
              element={<AppointmentDetailPage />}
            />
            <Route path="medical-records" element={<MedicalRecordsPage />} />
            <Route
              path="medical-records/files/:documentId"
              element={<DocumentViewerPage />}
            />
            <Route
              path="medical-records/:recordId"
              element={<MedicalRecordDetailPage />}
            />
            <Route path="departments" element={<DepartmentsPage />} />
            <Route path="resources" element={<ResourcesPage />} />
            <Route path="announcements" element={<AnnouncementsPage />} />
            <Route path="ai" element={<AICenterPage />} />
            <Route path="ai/intake" element={<IntakeAgentPage />} />
            <Route
              path="ai/intake/history"
              element={<Navigate to="/ai/intake" replace />}
            />
            <Route path="ai/diagnosis" element={<DiagnosisAgentPage />} />
            <Route path="ai/research" element={<ResearchAgentPage />} />
            <Route path="ai/prescription" element={<PrescriptionAgentPage />} />
            <Route
              path="ai/medical-report"
              element={<MedicalReportAgentPage />}
            />
            <Route path="ai/orchestrator" element={<AIOrchestratorPage />} />
            <Route path="ai/scheduling" element={<SchedulingAgentPage />} />
            <Route path="ai/emergency" element={<EmergencyAgentPage />} />
            <Route path="ai/resource-allocation" element={<ResourceAllocationAgentPage />} />
            <Route
              path="ai/digital-twin"
              element={
                <AIAgentPlaceholderPage
                  title="Digital Twin"
                  description="Hospital capacity and flow simulation."
                />
              }
            />
            <Route
              path="ai/insurance"
              element={
                <AIAgentPlaceholderPage
                  title="Insurance Agent"
                  description="Coverage checks and claim assistance."
                />
              }
            />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
