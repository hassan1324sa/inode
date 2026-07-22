import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  activePanel: 'palette' | 'properties' | 'none';
  sidebarWidth: number;
  panelWidth: number;
  theme: 'dark' | 'light' | 'system';
  commandPaletteOpen: boolean;

  toggleSidebar: () => void;
  setActivePanel: (panel: 'palette' | 'properties' | 'none') => void;
  setSidebarWidth: (width: number) => void;
  setPanelWidth: (width: number) => void;
  setTheme: (theme: 'dark' | 'light' | 'system') => void;
  toggleCommandPalette: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
}

export const useUIProjection = create<UIState>((set) => ({
  sidebarOpen: true,
  activePanel: 'palette',
  sidebarWidth: 260,
  panelWidth: 320,
  theme: (localStorage.getItem('theme') as 'dark' | 'light' | 'system') || 'dark',
  commandPaletteOpen: false,

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActivePanel: (panel) => set({ activePanel: panel }),
  setSidebarWidth: (width) => {
    localStorage.setItem('sidebarWidth', String(width));
    set({ sidebarWidth: width });
  },
  setPanelWidth: (width) => {
    localStorage.setItem('panelWidth', String(width));
    set({ panelWidth: width });
  },
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(theme);
    }
    set({ theme });
  },
  toggleCommandPalette: () => set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
}));
