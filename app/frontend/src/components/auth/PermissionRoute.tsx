import type {ReactNode} from 'react';
import {useAuth} from '@/contexts/AuthContext';
import {useIntl} from '@/contexts/IntlContext';

export function PermissionRoute({
  permission,
  superAdmin = false,
  children,
}: {
  permission?: string;
  superAdmin?: boolean;
  children: ReactNode;
}) {
  const {hasPermission, user} = useAuth();
  const {t} = useIntl();
  if ((superAdmin && !user?.is_super_admin) || (permission && !hasPermission(permission))) return <main className="center"><h1>{t("common.forbidden")}</h1></main>;
  return <>{children}</>;
}
