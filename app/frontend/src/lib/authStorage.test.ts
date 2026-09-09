import {beforeEach, describe, expect, it} from 'vitest';
import {clearAuth, readUser, STORAGE_KEYS} from './authStorage';

describe('auth storage', () => {
  beforeEach(() => localStorage.clear());
  it('rejects malformed stored users and clears both session keys', () => {
    localStorage.setItem(STORAGE_KEYS.user, '{');
    localStorage.setItem(STORAGE_KEYS.accessToken, 'token');
    expect(readUser()).toBeNull();
    clearAuth();
    expect(localStorage.length).toBe(0);
  });
});

