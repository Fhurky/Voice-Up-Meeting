import {Navigate, Outlet, useLocation} from 'react-router';
import {useAuth} from '@/contexts/AuthContext';

export function AuthGuard() {
  const {user, loading} = useAuth();
  const location = useLocation();
  if (loading) return <main className="center">Loading…</main>;
  if (!user) return <Navigate to="/login" replace state={{from: location.pathname}} />;
  return <Outlet />;
}

