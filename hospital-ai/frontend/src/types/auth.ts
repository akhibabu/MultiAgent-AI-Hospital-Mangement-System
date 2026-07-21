export type UserRole = 'Admin' | 'Doctor' | 'Nurse' | 'Receptionist';

export interface UserProfile {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in?: number | null;
}

export interface LoginResponse {
  tokens: AuthTokens;
  user: UserProfile;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface MessageResponse {
  message: string;
}
