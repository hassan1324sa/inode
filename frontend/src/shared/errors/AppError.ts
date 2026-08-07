export type AppErrorKind =
  | 'VALIDATION'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'SERVER_ERROR'
  | 'NETWORK';

export class AppError extends Error {
  public readonly kind: AppErrorKind;
  public readonly statusCode?: number;
  public readonly details?: unknown;

  constructor(message: string, kind: AppErrorKind, statusCode?: number, details?: unknown) {
    super(message);
    this.name = 'AppError';
    this.kind = kind;
    this.statusCode = statusCode;
    this.details = details;
    Object.setPrototypeOf(this, new.target.prototype);
  }

  public isNotFound(): boolean {
    return this.kind === 'NOT_FOUND';
  }

  public isNetworkOrOffline(): boolean {
    return this.kind === 'NETWORK' || (this.statusCode !== undefined && this.statusCode >= 500);
  }

  public static fromHttpResponse(status: number, message?: string, details?: unknown): AppError {
    if (status === 400) {
      return new AppError(message || 'Invalid request payload', 'VALIDATION', status, details);
    }
    if (status === 401) {
      return new AppError(message || 'Authentication required', 'UNAUTHORIZED', status, details);
    }
    if (status === 403) {
      return new AppError(message || 'Access forbidden', 'FORBIDDEN', status, details);
    }
    if (status === 404) {
      return new AppError(message || 'Resource not found', 'NOT_FOUND', status, details);
    }
    if (status === 409) {
      return new AppError(message || 'Resource conflict', 'CONFLICT', status, details);
    }
    if (status >= 500) {
      return new AppError(message || 'Server error occurred', 'SERVER_ERROR', status, details);
    }
    return new AppError(message || `HTTP error ${status}`, 'SERVER_ERROR', status, details);
  }

  public static network(message?: string): AppError {
    return new AppError(message || 'Backend service is unavailable. Please check your network connection.', 'NETWORK');
  }
}
