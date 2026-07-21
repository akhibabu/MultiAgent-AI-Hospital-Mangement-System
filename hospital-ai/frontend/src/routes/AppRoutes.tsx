import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from '@/components/common/ProtectedRoute';
import PublicOnlyRoute from '@/components/common/PublicOnlyRoute';
import MainLayout from '@/layouts/MainLayout';
import DashboardPage from '@/pages/Dashboard/DashboardPage';
import PatientsPage from '@/pages/Patients/PatientsPage';
import DoctorsPage from '@/pages/Doctors/DoctorsPage';
import AppointmentsPage from '@/pages/Appointments/AppointmentsPage';
import MedicalRecordsPage from '@/pages/MedicalRecords/MedicalRecordsPage';
import DepartmentsPage from '@/pages/Departments/DepartmentsPage';
import ResourcesPage from '@/pages/Resources/ResourcesPage';
import ProfilePage from '@/pages/Profile/ProfilePage';
import LoginPage from '@/pages/Login/LoginPage';
import NotFoundPage from '@/pages/NotFoundPage';

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="patients" element={<PatientsPage />} />
          <Route path="doctors" element={<DoctorsPage />} />
          <Route path="appointments" element={<AppointmentsPage />} />
          <Route path="medical-records" element={<MedicalRecordsPage />} />
          <Route path="departments" element={<DepartmentsPage />} />
          <Route path="resources" element={<ResourcesPage />} />
          <Route path="profile" element={<ProfilePage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
