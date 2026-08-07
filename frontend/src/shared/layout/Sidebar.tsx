import React from 'react';
import { NavLink } from 'react-router-dom';
import * as Icons from 'lucide-react';
import { useUIProjection } from '../../features/builder/application/services';

export const Sidebar: React.FC = () => {
  const { theme, setTheme } = useUIProjection();

  const navItems = [
    { name: 'Workflows', path: '/workflows', icon: 'Workflow' },
    { name: 'Executions', path: '/executions', icon: 'Activity' },
    { name: 'Credentials', path: '/credentials', icon: 'Key' },
    { name: 'Settings', path: '/settings', icon: 'Sliders' },
  ];

  return (
    <div className="w-[260px] h-full flex flex-col justify-between text-left p-4 skeuo-raised rounded-r-2xl border-l-0">
      <div className="space-y-6">
        {/* Logo */}
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary to-purple-600 flex items-center justify-center text-white font-black shadow-lg shadow-primary/30 border border-primary/40" style={{ boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.4), 0 3px 6px rgba(0,0,0,0.4)' }}>
            F
          </div>
          <span className="font-extrabold text-lg text-foreground tracking-tight" style={{ textShadow: '1px 1px 2px rgba(0,0,0,0.5)' }}>Fluxa</span>
        </div>


        {/* Navigation List */}
        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = (Icons as any)[item.icon] || Icons.HelpCircle;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => {
                  // Ensure /workflows/:id builder context activates the Workflows tab
                  const isWorkflowsContext = item.path === '/workflows' && window.location.pathname.startsWith('/workflows');
                  const active = isActive || isWorkflowsContext;
                  return `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all duration-150 border border-transparent ${
                    active
                      ? 'bg-primary text-white border-black/40 shadow-inner'
                      : 'text-muted-foreground bg-gradient-to-b from-secondary to-muted hover:text-foreground hover:border-border'
                  }`;
                }}
                style={({ isActive }) => {
                  const isWorkflowsContext = item.path === '/workflows' && window.location.pathname.startsWith('/workflows');
                  const active = isActive || isWorkflowsContext;
                  return active ? { boxShadow: 'inset 1px 2px 4px rgba(0,0,0,0.6)' } : { boxShadow: 'inset 0 1px 0px rgba(255,255,255,0.08), 0 2px 4px rgba(0,0,0,0.3)' };
                }}
              >
                <Icon size={16} />
                {item.name}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer / Theme Toggle */}
      <div className="pt-4 border-t border-black/40 flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground font-mono">v1.0.0</span>
        <button
          onClick={() => {
            const nextTheme = theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark';
            setTheme(nextTheme);
          }}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold text-muted-foreground hover:text-foreground skeuo-btn flex items-center gap-1.5 transition-all"
          title={`Current Theme: ${theme.toUpperCase()} (click to switch)`}
        >
          {theme === 'dark' ? (
            <>
              <Icons.Moon size={14} className="text-purple-400" />
              <span>Dark</span>
            </>
          ) : theme === 'light' ? (
            <>
              <Icons.Sun size={14} className="text-amber-500" />
              <span>Light</span>
            </>
          ) : (
            <>
              <Icons.Monitor size={14} className="text-blue-400" />
              <span>Auto</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
export default Sidebar;

