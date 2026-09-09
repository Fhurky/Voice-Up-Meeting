import type {ReactNode} from 'react';
import {useAuth} from '@/contexts/AuthContext';
import {useIntl} from '@/contexts/IntlContext';

export function PermissionRoute({
  permission,
  children,
}: {
  permission?: string;
  children: ReactNode;
}) {
  const {hasPermission} = useAuth();
  const {t} = useIntl();
  if (permission && !hasPermission(permission)) return <main className="center"><h1>{t("common.forbidden")}</h1></main>;
  return <>{children}</>;
}
