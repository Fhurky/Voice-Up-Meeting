import type {ReactNode} from 'react';
import {useAuth} from '@/contexts/AuthContext';

export function PermissionRoute({
  permission,
  children,
}: {
  permission?: string;
  children: ReactNode;
}) {
  const {hasPermission} = useAuth();
  if (permission && !hasPermission(permission)) return <main><h1>Forbidden</h1></main>;
  return <>{children}</>;
}

