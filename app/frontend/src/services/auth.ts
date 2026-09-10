import {apiRequest} from '@/lib/apiClient';
import type {AuthenticatedUser, AuthOptions, LoginResponse} from '@/types/auth';

export const AuthService = {
  options(): Promise<AuthOptions> {
    return apiRequest<AuthOptions>('/auth/options', {method: 'GET', cache: 'no-store'}, false);
  },
  loginAsAdmin(): Promise<LoginResponse> {
    return apiRequest<LoginResponse>('/auth/local-admin', {method: 'POST', cache: 'no-store'}, false);
  },
  login(username: string, password: string): Promise<LoginResponse> {
    return apiRequest<LoginResponse>(
      '/auth/login',
      {method: 'POST', body: JSON.stringify({username, password})},
      false,
    );
  },
  me(): Promise<AuthenticatedUser> {
    return apiRequest<AuthenticatedUser>('/auth/me');
  },
};
