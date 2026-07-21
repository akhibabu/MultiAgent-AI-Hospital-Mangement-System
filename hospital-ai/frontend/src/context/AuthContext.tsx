import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Session } from '@supabase/supabase-js';
import { authService } from '@/services/authService';
import { supabase } from '@/services/supabaseClient';
import type { LoginCredentials, UserProfile, UserRole } from '@/types/auth';

interface AuthContextValue {
  user: UserProfile | null;
  role: UserRole | null;
  session: Session | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<UserProfile>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const USER_QUERY_KEY = ['auth', 'me'] as const;

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<Session | null>(null);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setSessionReady(true);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setSessionReady(true);
      if (!nextSession) {
        queryClient.removeQueries({ queryKey: USER_QUERY_KEY });
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [queryClient]);

  const {
    data: user = null,
    isLoading: isUserLoading,
    refetch,
  } = useQuery({
    queryKey: USER_QUERY_KEY,
    queryFn: () => authService.getMe(),
    enabled: sessionReady && Boolean(session?.access_token),
    retry: false,
    staleTime: 5 * 60_000,
  });

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const result = await authService.login(credentials);
      queryClient.setQueryData(USER_QUERY_KEY, result.user);
      return result.user;
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    await authService.logout();
    queryClient.removeQueries({ queryKey: USER_QUERY_KEY });
    setSession(null);
  }, [queryClient]);

  const refreshUser = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      role: user?.role ?? null,
      session,
      isAuthenticated: Boolean(session && user),
      isLoading: !sessionReady || (Boolean(session) && isUserLoading),
      login,
      logout,
      refreshUser,
    }),
    [
      user,
      session,
      sessionReady,
      isUserLoading,
      login,
      logout,
      refreshUser,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
