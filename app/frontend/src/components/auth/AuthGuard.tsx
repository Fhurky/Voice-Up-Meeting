import {Navigate, Outlet, useLocation} from 'react-router';
import {useAuth} from '@/contexts/AuthContext';
import {useIntl} from '@/contexts/IntlContext';

export function AuthGuard() {
  const {user, loading} = useAuth();
  const location = useLocation();
  const {t} = useIntl();
  if (loading) return <main className="center">{t("common.loading")}</main>;
  if (!user) return <Navigate to="/login" replace state={{from: location.pathname}} />;
  return <Outlet />;
}
