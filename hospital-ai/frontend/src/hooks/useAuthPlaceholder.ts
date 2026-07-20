import { useState, useEffect } from 'react';

/**
 * Placeholder hook for future authenticated session state.
 * Auth is intentionally not implemented in Week 1 Step 1.
 */
export function useAuthPlaceholder() {
  const [isAuthenticated, setIsAuthenticated] = useState(true);

  useEffect(() => {
    // Session checks will be wired to Supabase Auth in a later step
  }, []);

  return {
    isAuthenticated,
    setIsAuthenticated,
  };
}
