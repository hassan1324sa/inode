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
    let message = data.detail || data.message || `API Error ${response.status}`;
    if (typeof message === 'object') {
      if (Array.isArray(message)) {
        message = message.map((err: any) => err.msg || JSON.stringify(err)).join(', ');
      } else {
        message = JSON.stringify(message);
      }
    }
    throw new Error(`${message}`);
  }
  
  return data;
}

/**
 * Wrapper around standard fetch to automatically attach:
 * 1. Bearer Authorization header if token exists in session
 * 2. Default Content-Type: application/json for POST/PUT requests
 */
let refreshPromise: Promise<string> | null = null;

async function performRefresh(): Promise<string> {
  const refreshToken = sessionManager.getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  const res = await fetch('/api/v1/auth/refresh/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) {
    throw new Error('Refresh request failed');
  }

  const data = await res.json();
  if (!data.access_token || !data.refresh_token) {
    throw new Error('Invalid refresh response payload');
  }

  sessionManager.setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

export async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = sessionManager.getToken();
  const headers = new Headers(init?.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response = await fetch(input, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    const isRefreshRequest = typeof input === 'string' && input.includes('/auth/refresh/');
    if (!isRefreshRequest) {
      try {
        if (!refreshPromise) {
          refreshPromise = performRefresh().finally(() => {
            refreshPromise = null;
          });
        }
        const newAccessToken = await refreshPromise;
        
        // Retry the original request with the new access token
        const retryHeaders = new Headers(init?.headers || {});
        retryHeaders.set('Authorization', `Bearer ${newAccessToken}`);
        response = await fetch(input, {
          ...init,
          headers: retryHeaders,
        });
      } catch (err) {
        console.error("Token refresh failed, redirecting to login:", err);
        sessionManager.clearSession();
        window.location.href = '/login';
      }
    }
  }

  return response;
}
