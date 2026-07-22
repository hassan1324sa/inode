import React from 'react';
import { NavLink } from 'react-router-dom';
import * as Icons from 'lucide-react';
import { useUIProjection } from '../../features/builder/application/services';

export const Sidebar: React.FC = () => {
  const { theme, setTheme } = useUIProjection();

  const navItems = [
    { name: 'Canvas Builder', path: '/', icon: 'Workflow' },
    { name: 'Executions', path: '/executions', icon: 'Activity' },
    { name: 'Credentials', path: '/credentials', icon: 'Key' },
    { name: 'Settings', path: '/settings', icon: 'Sliders' },
  ];

  return (
    <div className="w-[260px] h-full border-r border-border glass flex flex-col justify-between text-left p-4">
      <div className="space-y-6">
        {/* Logo */}
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-purple-500 flex items-center justify-center text-white font-bold shadow-md shadow-primary/20">
            F
          </div>
          <span className="font-extrabold text-lg text-foreground tracking-tight">Fluxa</span>
        </div>

        {/* Navigation List */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = (Icons as any)[item.icon] || Icons.HelpCircle;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                    isActive
                      ? 'bg-primary text-white shadow-md shadow-primary/10'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                  }`
                }
              >
                <Icon size={16} />
                {item.name}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer / Theme Toggle */}
      <div className="pt-4 border-t border-border/50 flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground font-mono">v1.0.0</span>
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          title="Toggle Light/Dark Theme"
        >
          {theme === 'dark' ? <Icons.Sun size={15} /> : <Icons.Moon size={15} />}
        </button>
      </div>
    </div>
  );
};
export default Sidebar;
