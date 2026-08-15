import { QueryClient } from '@tanstack/react-query';
import { useWorkflowProjection } from '../../features/builder/infrastructure/projections/workflowProjection';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

export interface SessionContext {
  userId: string | null;
  organizationId: string | null;
  token: string | null;
  refreshToken?: string | null;
}

class SessionManager {
  private currentContext: SessionContext = {
    userId: null,
    organizationId: null,
    token: null,
    refreshToken: null,
  };

  /**
   * Set new active Session / Organization Context.
   * Performs targeted invalidation of workspace-scoped queries & clears Zustand state
   * WITHOUT wiping global UI preferences (e.g. theme, grid settings).
   */
  public setSession(newContext: SessionContext) {
    const isContextChanged =
      this.currentContext.organizationId !== newContext.organizationId ||
      this.currentContext.userId !== newContext.userId ||
      this.currentContext.token !== newContext.token;

    this.currentContext = { ...newContext };

    if (newContext.token) {
      localStorage.setItem('fluxa_auth_token', newContext.token);
    } else {
      localStorage.removeItem('fluxa_auth_token');
    }

    if (newContext.refreshToken) {
      localStorage.setItem('fluxa_refresh_token', newContext.refreshToken);
    } else if (newContext.refreshToken === null) {
      localStorage.removeItem('fluxa_refresh_token');
    }

    if (isContextChanged) {
      this.invalidateWorkspaceData();
    }
  }

  /**
   * Clear session on Logout or Auth Failure.
   */
  public clearSession() {
    this.currentContext = { userId: null, organizationId: null, token: null, refreshToken: null };
    localStorage.removeItem('fluxa_auth_token');
    localStorage.removeItem('fluxa_refresh_token');
    this.invalidateWorkspaceData();
  }

  /**
   * Target Invalidation: Invalidate queries and reset workspace Zustand projection state,
   * while keeping global UI preferences intact (e.g., fluxa_ui_show_grid, theme).
   */
  private invalidateWorkspaceData() {
    // 1. Target TanStack Query workspace invalidation
    queryClient.invalidateQueries({ queryKey: ['workflows'] });
    queryClient.invalidateQueries({ queryKey: ['executions'] });
    queryClient.invalidateQueries({ queryKey: ['credentials'] });
    queryClient.invalidateQueries({ queryKey: ['organization'] });

    // 2. Clear active Workflow Zustand Projection State
    useWorkflowProjection.getState().clearState();

    // 3. Clear workspace-scoped local storage caches while preserving global UI preferences
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('workflow_') || key.startsWith('fluxa_cache_'))) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((k) => localStorage.removeItem(k));
  }

  public getSession(): SessionContext {
    return { ...this.currentContext };
  }

  public getToken(): string | null {
    return localStorage.getItem('fluxa_auth_token');
  }

  public getRefreshToken(): string | null {
    return localStorage.getItem('fluxa_refresh_token');
  }

  public setTokens(token: string, refreshToken: string) {
    this.currentContext.token = token;
    this.currentContext.refreshToken = refreshToken;
    localStorage.setItem('fluxa_auth_token', token);
    localStorage.setItem('fluxa_refresh_token', refreshToken);
  }
}

export const sessionManager = new SessionManager();
