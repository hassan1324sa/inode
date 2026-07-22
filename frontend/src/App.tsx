import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Sidebar from './shared/layout/Sidebar';
import BuilderPage from './pages/BuilderPage';
import ExecutionsPage from './pages/ExecutionsPage';
import SettingsPage from './pages/SettingsPage';
import CredentialsPage from './pages/CredentialsPage';
import './App.css';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
          {/* Global Sidebar Shell */}
          <Sidebar />

          {/* Page Routing Container */}
          <div className="flex-1 h-full flex flex-col overflow-hidden">
            <Routes>
              <Route path="/" element={<BuilderPage />} />
              <Route path="/executions" element={<ExecutionsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/credentials" element={<CredentialsPage />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
