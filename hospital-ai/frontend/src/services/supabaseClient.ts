import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { getAuthStorage } from '@/services/authStorage';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    '[Hospital AI] VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are not set. '
      + 'Copy frontend/.env.example to frontend/.env and add your Supabase keys.',
  );
}

/**
 * Shared Supabase browser client.
 * Use this everywhere instead of creating new clients.
 */
export const supabase: SupabaseClient = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseAnonKey || 'placeholder-anon-key',
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      storage: {
        getItem: (key) => getAuthStorage().getItem(key),
        setItem: (key, value) => getAuthStorage().setItem(key, value),
        removeItem: (key) => {
          window.localStorage.removeItem(key);
          window.sessionStorage.removeItem(key);
        },
      },
    },
  },
);

export default supabase;
