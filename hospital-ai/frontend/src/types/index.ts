export interface NavItem {
  label: string;
  path: string;
  icon?: string;
}

export interface PageMeta {
  title: string;
  description: string;
}

export type ThemeMode = 'light' | 'dark';

export type {
  AuthTokens,
  LoginCredentials,
  LoginResponse,
  MessageResponse,
  UserProfile,
  UserRole,
} from '@/types/auth';

export type {
  BloodGroup,
  Patient,
  PatientAIExtensions,
  PatientFormValues,
  PatientGender,
  PatientListParams,
  PatientListResponse,
} from '@/types/patient';
