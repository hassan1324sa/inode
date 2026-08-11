import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionManager } from '../shared/session/sessionManager';
import { useToast } from '../shared/components/Toast';
import { parseApiResponse } from '../shared/api/authenticatedFetch';

export function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const baseUrl = '/api/v1/auth';
    
    try {
      if (!isLogin) {
        // Register flow
        const regRes = await fetch(`${baseUrl}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, name: name || 'User' }),
        });
        
        await parseApiResponse(regRes);
      }

      // Login flow
      const loginRes = await fetch(`${baseUrl}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await parseApiResponse(loginRes);
      
      // The backend returns access_token
      if (data.access_token) {
        // Parse basic details from JWT payload without verification
        try {
          const payload = JSON.parse(atob(data.access_token.split('.')[1]));
          sessionManager.setSession({
            token: data.access_token,
            userId: payload.sub || null,
            organizationId: payload.org_id || null,
          });
        } catch (e) {
          console.warn("Failed to parse JWT", e);
          sessionManager.setSession({
            token: data.access_token,
            userId: null,
            organizationId: null,
          });
        }
        showToast(`Successfully logged in`, 'success');
        navigate('/workflows', { replace: true });
      } else {
        throw new Error('No access token returned from server');
      }
    } catch (err: any) {
      setError(err.message || 'Authentication error');
      showToast(err.message || 'Authentication error', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full w-full items-center justify-center bg-background">
      <div className="w-full max-w-md p-8 bg-card rounded-lg shadow-xl shadow-black/40 border border-border">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-black text-primary mb-2">Fluxa Auth</h1>
          <p className="text-sm text-muted-foreground">
            {isLogin ? 'Sign in to your account' : 'Create a new developer account'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-500 text-sm font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div className="space-y-2">
              <label className="text-sm font-bold text-foreground">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="Developer"
              />
            </div>
          )}
          
          <div className="space-y-2">
            <label className="text-sm font-bold text-foreground">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="dev@fluxa.ai"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-bold text-foreground">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-bold py-2 px-4 rounded-md shadow-md transition-all mt-6 disabled:opacity-50"
          >
            {loading ? 'Processing...' : isLogin ? 'Sign In' : 'Register & Sign In'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="text-xs text-muted-foreground hover:text-primary transition-colors"
          >
            {isLogin ? "Don't have an account? Register" : 'Already have an account? Sign In'}
          </button>
        </div>
      </div>
    </div>
  );
}
