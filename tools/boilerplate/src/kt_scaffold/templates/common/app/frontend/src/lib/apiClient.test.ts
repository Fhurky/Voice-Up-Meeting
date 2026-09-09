import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {apiRequest} from './apiClient';
import {STORAGE_KEYS} from './authStorage';

describe('api client', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it('sends bearer and tenant context together', async () => {
    localStorage.setItem(STORAGE_KEYS.accessToken, 'jwt');
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify({tenant_id: 'tenant-1'}));
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ok: true}), {status: 200, headers: {'Content-Type': 'application/json'}}),
    );
    await apiRequest('/auth/me');
    const request = fetchMock.mock.calls[0][1]!;
    const headers = new Headers(request.headers);
    expect(headers.get('Authorization')).toBe('Bearer jwt');
    expect(headers.get('@@TENANT_HEADER@@')).toBe('tenant-1');
  });

  it('clears the local session on every unauthorized response', async () => {
    window.history.replaceState({}, '', '/login');
    localStorage.setItem(STORAGE_KEYS.accessToken, 'expired');
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify({tenant_id: 'tenant-1'}));
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({message: ['Token expired']}), {
        status: 401,
        headers: {'Content-Type': 'application/json'},
      }),
    );

    await expect(apiRequest('/auth/me')).rejects.toMatchObject({
      status: 401,
      message: 'Token expired',
    });
    expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBeNull();
    expect(localStorage.getItem(STORAGE_KEYS.user)).toBeNull();
  });
});
