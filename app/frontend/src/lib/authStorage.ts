import type {AuthenticatedUser, LoginResponse} from '@/types/auth';

export const STORAGE_KEYS = {
  accessToken: 'voiceup.access_token',
  user: 'voiceup.user',
} as const;

export function readUser(): AuthenticatedUser | null {
  try {
    const value = localStorage.getItem(STORAGE_KEYS.user);
    return value ? (JSON.parse(value) as AuthenticatedUser) : null;
  } catch {
    return null;
  }
}

export function clearAuth(): void {
  localStorage.removeItem(STORAGE_KEYS.accessToken);
  localStorage.removeItem(STORAGE_KEYS.user);
}

export function saveUser(user: AuthenticatedUser): void {
  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user));
}

export function saveAuth(response: LoginResponse): void {
  try {
    localStorage.setItem(STORAGE_KEYS.accessToken, response.access_token);
    saveUser(response.user);
  } catch (error) {
    clearAuth();
    throw error;
  }
}
