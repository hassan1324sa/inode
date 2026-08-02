import React, { createContext, useContext, useState, useCallback } from 'react';
import * as Icons from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType, duration?: number) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, type: ToastType = 'info', duration = 4000) => {
    const id = `toast-${Math.random().toString(36).substr(2, 9)}`;
    setToasts((prev) => [...prev, { id, message, type, duration }]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((toast) => {
          const isSuccess = toast.type === 'success';
          const isError = toast.type === 'error';
          const isWarning = toast.type === 'warning';

          const bgColor = isSuccess
            ? 'bg-emerald-950/90 border-emerald-500/30 text-emerald-300'
            : isError
            ? 'bg-red-950/90 border-red-500/30 text-red-300'
            : isWarning
            ? 'bg-amber-950/90 border-amber-500/30 text-amber-300'
            : 'bg-slate-900/90 border-slate-700 text-slate-200';

          const IconComp = isSuccess
            ? Icons.CheckCircle2
            : isError
            ? Icons.AlertCircle
            : isWarning
            ? Icons.AlertTriangle
            : Icons.Info;

          return (
            <div
              key={toast.id}
              className={`flex items-center justify-between p-3.5 rounded-xl border shadow-xl backdrop-blur-md pointer-events-auto transition-all animate-in fade-in slide-in-from-bottom-2 ${bgColor}`}
            >
              <div className="flex items-center gap-2.5 text-xs font-semibold">
                <IconComp size={16} className="shrink-0" />
                <span>{toast.message}</span>
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="p-1 hover:bg-white/10 rounded-md transition-colors"
                title="Close"
              >
                <Icons.X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
