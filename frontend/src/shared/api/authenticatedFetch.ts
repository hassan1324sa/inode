import { sessionManager } from '../session/sessionManager';

/**
 * Wrapper around standard fetch to automatically attach:
 * 1. Bearer Authorization header if token exists in session
 * 2. Default Content-Type: application/json for POST/PUT requests
 */
export async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = sessionManager.getToken();
  const headers = new Headers(init?.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(input, {
    ...init,
    headers,
  });
}
