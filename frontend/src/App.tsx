import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import Sidebar from './shared/layout/Sidebar';
import BuilderPage from './pages/BuilderPage';
import ExecutionsPage from './pages/ExecutionsPage';
import SettingsPage from './pages/SettingsPage';
import CredentialsPage from './pages/CredentialsPage';
import { WorkflowsPage } from './pages/WorkflowsPage';
import './App.css';

import { ToastProvider } from './shared/components/Toast';
import { ThemeProvider } from './shared/components/ThemeProvider';

import { queryClient } from './shared/session/sessionManager';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ThemeProvider>
          <BrowserRouter>
            <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
              {/* Global Sidebar Shell */}
              <Sidebar />

              {/* Page Routing Container */}
              <div className="flex-1 h-full flex flex-col overflow-hidden">
                <Routes>
                  <Route path="/" element={<Navigate to="/workflows" replace />} />
                  <Route path="/workflows" element={<WorkflowsPage />} />
                  <Route path="/workflows/:workflowId" element={<BuilderPage />} />
                  <Route path="/executions" element={<ExecutionsPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="/credentials" element={<CredentialsPage />} />
                  <Route
                    path="*"
                    element={
                      <div className="flex-1 h-full flex flex-col items-center justify-center text-center p-6 bg-background">
                        <div className="text-6xl font-black text-primary mb-4">404</div>
                        <h2 className="text-xl font-bold text-foreground mb-2">Page Not Found</h2>
                        <p className="text-sm text-muted-foreground mb-6">
                          The page you are looking for does not exist or has been moved.
                        </p>
                        <a
                          href="/"
                          className="px-4 py-2 bg-primary hover:bg-primary/90 text-white text-xs font-bold rounded-md shadow-md shadow-primary/20 transition-all"
                        >
                          Return to Canvas
                        </a>
                      </div>
                    }
                  />
                </Routes>
              </div>
            </div>
          </BrowserRouter>
        </ThemeProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}


export default App;
