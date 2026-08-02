import React, { useEffect } from 'react';
import { useUIProjection } from '../../features/builder/application/services';

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { theme } = useUIProjection();

  useEffect(() => {
    const root = window.document.documentElement;
    const body = window.document.body;

    const applyTheme = (targetTheme: 'dark' | 'light' | 'system') => {
      root.classList.remove('light', 'dark');
      body.classList.remove('light', 'dark');

      const resolvedTheme =
        targetTheme === 'system'
          ? window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light'
          : targetTheme;

      root.classList.add(resolvedTheme);
      body.classList.add(resolvedTheme);
      root.style.colorScheme = resolvedTheme;
    };

    applyTheme(theme);

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const listener = () => applyTheme('system');
      mediaQuery.addEventListener('change', listener);
      return () => mediaQuery.removeEventListener('change', listener);
    }
  }, [theme]);

  return <>{children}</>;
};

export default ThemeProvider;
