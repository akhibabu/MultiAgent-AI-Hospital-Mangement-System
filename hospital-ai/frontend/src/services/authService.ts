import apiClient from '@/services/apiClient';
import { supabase } from '@/services/supabaseClient';
import { setRememberPreference } from '@/services/authStorage';
import type {
  LoginCredentials,
  LoginResponse,
  MessageResponse,
  UserProfile,
} from '@/types/auth';

/**
 * Auth API service — backend endpoints + local Supabase session sync.
 */
export const authService = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    setRememberPreference(Boolean(credentials.rememberMe));

    const { data } = await apiClient.post<LoginResponse>('/auth/login', {
      email: credentials.email.trim(),
      password: credentials.password,
    });

    const { error } = await supabase.auth.setSession({
      access_token: data.tokens.access_token,
      refresh_token: data.tokens.refresh_token,
    });

    if (error) {
      throw new Error(error.message || 'Failed to persist session');
    }

    return data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post<MessageResponse>('/auth/logout');
    } catch {
      // Always clear local session even if the API call fails.
    } finally {
      await supabase.auth.signOut();
    }
  },

  async getMe(): Promise<UserProfile> {
    const { data } = await apiClient.get<UserProfile>('/auth/me');
    return data;
  },

  async getAccessToken(): Promise<string | null> {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  },

  async getSession() {
    const { data } = await supabase.auth.getSession();
    return data.session;
  },
};

export default authService;
