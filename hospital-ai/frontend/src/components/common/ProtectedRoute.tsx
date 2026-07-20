import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthPlaceholder } from '@/hooks/useAuthPlaceholder';
import Loading from '@/components/ui/Loading';

/**
 * Route guard scaffold. Real Supabase Auth checks will replace
 * the placeholder hook in a later week.
 */
export default function ProtectedRoute() {
  const { isAuthenticated } = useAuthPlaceholder();
  const location = useLocation();

  // Brief loading affordance for future async session resolution
  if (isAuthenticated === undefined) {
    return <Loading fullScreen message="Checking session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
