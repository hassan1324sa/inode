import { sessionManager } from '../session/sessionManager';

/**
 * Safely parse JSON from a response, handling empty bodies and text fallbacks
 * to prevent "Unexpected end of JSON input" errors.
 */
export async function parseApiResponse<T = any>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  
  let data;
  try {
    const text = await response.text();
    if (!text) {
      if (response.ok) return {} as T;
      throw new Error(`Empty response body from server (Status: ${response.status})`);
    }
    
    if (isJson) {
      data = JSON.parse(text);
    } else {
      if (response.ok) return text as any;
      throw new Error(`Unexpected non-JSON response (Status: ${response.status}): ${text.substring(0, 100)}`);
    }
  } catch (err: any) {
    if (!response.ok) {
      throw new Error(`API Error ${response.status}: ${err.message}`);
    }
    throw new Error(`Failed to parse response: ${err.message}`);
  }
  
  if (!response.ok) {
    const message = data.detail || data.message || `API Error ${response.status}`;
    throw new Error(`${message}`);
  }
  
  return data;
}

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

  const response = await fetch(input, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    sessionManager.clearSession();
    window.location.href = '/login';
  }

  return response;
}
