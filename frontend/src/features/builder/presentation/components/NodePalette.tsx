import React from 'react';
import * as Icons from 'lucide-react';
import { SearchNodesHandler, SearchNodesQuery } from '../../application/queries/searchNodes';
import type { NodePlugin } from '../../domain/plugins/plugin';

interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, nodeType: string) => void;
  onOpenPackageBrowser?: () => void;
}

interface AccordionSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  plugins: NodePlugin[];
}

export const NodePalette: React.FC<NodePaletteProps> = ({ onDragStart, onOpenPackageBrowser }) => {
  const [searchTerm, setSearchTerm] = React.useState('');
  const [plugins, setPlugins] = React.useState<NodePlugin[]>([]);
  const [openSections, setOpenSections] = React.useState<Record<string, boolean>>({
    favorites: true,
    triggers: true,
    ai_logic: true,
    integrations: false,
    data_files: false,
    installed: true,
  });

  const [favorites, setFavorites] = React.useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('fluxa_favorite_nodes') || '[]');
    } catch { return []; }
  });
  const [recent, setRecent] = React.useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('fluxa_recent_nodes') || '[]');
    } catch { return []; }
  });

  const searchHandler = React.useMemo(() => new SearchNodesHandler(), []);

  React.useEffect(() => {
    searchHandler.execute(new SearchNodesQuery(searchTerm)).then(setPlugins);
  }, [searchTerm, searchHandler]);

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setFavorites((prev) => {
      const next = prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id];
      localStorage.setItem('fluxa_favorite_nodes', JSON.stringify(next));
      return next;
    });
  };

  const handleDragStart = (e: React.DragEvent, id: string) => {
    setRecent((prev) => {
      const filtered = prev.filter((item) => item !== id);
      const next = [id, ...filtered].slice(0, 8);
      localStorage.setItem('fluxa_recent_nodes', JSON.stringify(next));
      return next;
    });
    onDragStart(e, id);
  };

  const toggleSection = (sectionId: string) => {
    setOpenSections(prev => ({ ...prev, [sectionId]: !prev[sectionId] }));
  };

  // Group plugins into semantic accordion sections
  const sections = React.useMemo<AccordionSection[]>(() => {
    if (searchTerm.trim()) return [];

    const favPlugins = plugins.filter(p => favorites.includes(p.metadata.id));
    const recentPlugins = plugins.filter(p => recent.includes(p.metadata.id) && !favorites.includes(p.metadata.id));
    const triggerPlugins = plugins.filter(p => p.capabilities.trigger);
    const aiLogicPlugins = plugins.filter(p => ['AI', 'Logic'].includes(p.metadata.category) && !p.capabilities.trigger);
    const integrationPlugins = plugins.filter(p => ['HTTP', 'Communication', 'Utilities'].includes(p.metadata.category) && !p.capabilities.trigger);
    const dataFilesPlugins = plugins.filter(p => ['Data', 'Files', 'Variables'].includes(p.metadata.category) && !p.capabilities.trigger);
    const installedPlugins = plugins.filter(p => p.metadata.category === 'Installed Packages');

    const result: AccordionSection[] = [];

    if (favPlugins.length > 0) {
      result.push({
        id: 'favorites',
        title: 'Favorites',
        icon: <Icons.Star size={14} className="text-amber-400" fill="currentColor" />,
        plugins: favPlugins,
      });
    }

    if (recentPlugins.length > 0) {
      result.push({
        id: 'recent',
        title: 'Recent',
        icon: <Icons.History size={14} className="text-blue-400" />,
        plugins: recentPlugins,
      });
    }

    result.push(
      {
        id: 'triggers',
        title: 'Triggers',
        icon: <Icons.Zap size={14} className="text-emerald-400" />,
        plugins: triggerPlugins,
      },
      {
        id: 'ai_logic',
        title: 'AI & Core Logic',
        icon: <Icons.BrainCircuit size={14} className="text-purple-400" />,
        plugins: aiLogicPlugins,
      },
      {
        id: 'integrations',
        title: 'HTTP & Integrations',
        icon: <Icons.Globe size={14} className="text-blue-400" />,
        plugins: integrationPlugins,
      },
      {
        id: 'data_files',
        title: 'Data & Files',
        icon: <Icons.FolderOpen size={14} className="text-amber-500" />,
        plugins: dataFilesPlugins,
      }
    );

    if (installedPlugins.length > 0) {
      result.push({
        id: 'installed',
        title: 'Installed Packages',
        icon: <Icons.Package size={14} className="text-indigo-400" />,
        plugins: installedPlugins,
      });
    }

    return result;
  }, [plugins, favorites, recent, searchTerm]);

  const highlightText = (text: string, search: string) => {
    if (!search.trim()) return <span>{text}</span>;
    const escaped = search.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'gi');
    const parts = text.split(regex);
    return (
      <span>
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark key={i} className="bg-primary/30 text-primary-foreground font-semibold px-0.5 rounded-[2px]">
              {part}
            </mark>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </span>
    );
  };

  return (
    <div className="flex flex-col h-full border-r border-border p-4 bg-card/45 text-left overflow-hidden">
      {/* Title Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Icons.LayoutGrid className="text-primary animate-pulse" size={18} />
          <h3 className="font-extrabold text-sm text-foreground tracking-tight">Node Palette</h3>
        </div>
        {onOpenPackageBrowser && (
          <button
            onClick={onOpenOpenPackageBrowserHelper(onOpenPackageBrowser)}
            className="flex items-center gap-1.5 px-2.5 py-1.2 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary text-[10px] font-bold border border-primary/20 hover:border-primary/40 shadow-sm transition-all cursor-pointer"
            title="Browse Packages"
          >
            <Icons.PackageOpen size={12} />
            <span>Packages</span>
          </button>
        )}
      </div>

      {/* Search Bar */}
      <div className="relative mb-4">
        <Icons.Search className="absolute left-3 top-2.5 text-muted-foreground" size={14} />
        <input
          type="text"
          placeholder="Search nodes & extensions..."
          className="w-full pl-9 pr-3 py-2 rounded-xl text-xs bg-secondary/40 text-foreground border border-border/40 focus:border-primary/70 focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all placeholder:text-muted-foreground/60 shadow-inner"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        {searchTerm && (
          <button
            onClick={() => setSearchTerm('')}
            className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
          >
            <Icons.X size={13} />
          </button>
        )}
      </div>

      {/* Accordion / Flat list container */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin">
        {searchTerm.trim() ? (
          // Flat list search results
          <div className="space-y-2">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
              Search Results ({plugins.length})
            </span>
            {plugins.map((plugin) => (
              <NodeItem
                key={plugin.metadata.id}
                plugin={plugin}
                favorites={favorites}
                onDragStart={handleDragStart}
                onToggleFavorite={toggleFavorite}
                highlightText={highlightText}
                searchTerm={searchTerm}
              />
            ))}
            {plugins.length === 0 && (
              <div className="text-center py-12 text-muted-foreground text-xs flex flex-col items-center gap-2">
                <Icons.SearchX size={24} className="opacity-40" />
                <span>No nodes match your search query.</span>
              </div>
            )}
          </div>
        ) : (
          // Premium Accordion Groups
          sections.map((sec) => {
            const isOpen = openSections[sec.id] ?? false;
            return (
              <div key={sec.id} className="border border-border/30 rounded-xl bg-secondary/10 overflow-hidden shadow-sm">
                <button
                  onClick={() => toggleSection(sec.id)}
                  className="w-full px-3 py-2.5 flex items-center justify-between bg-secondary/30 hover:bg-secondary/50 transition-colors text-left"
                >
                  <div className="flex items-center gap-2">
                    {sec.icon}
                    <span className="font-bold text-[11px] text-foreground tracking-wide uppercase">{sec.title}</span>
                    <span className="text-[9px] px-1.5 py-0.2 bg-card/65 text-muted-foreground border border-border/30 rounded-full font-bold">
                      {sec.plugins.length}
                    </span>
                  </div>
                  <Icons.ChevronRight
                    size={14}
                    className={`text-muted-foreground transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`}
                  />
                </button>

                {isOpen && (
                  <div className="p-2 space-y-2 bg-card/20 border-t border-border/10">
                    {sec.plugins.map((plugin) => (
                      <NodeItem
                        key={plugin.metadata.id}
                        plugin={plugin}
                        favorites={favorites}
                        onDragStart={handleDragStart}
                        onToggleFavorite={toggleFavorite}
                        highlightText={highlightText}
                        searchTerm={searchTerm}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

// Helper to prevent synthetic event issues in react onClick handlers
const onOpenOpenPackageBrowserHelper = (cb: () => void) => (e: React.MouseEvent) => {
  e.preventDefault();
  cb();
};

interface NodeItemProps {
  plugin: NodePlugin;
  favorites: string[];
  onDragStart: (e: React.DragEvent, id: string) => void;
  onToggleFavorite: (id: string, e: React.MouseEvent) => void;
  highlightText: (text: string, search: string) => React.ReactNode;
  searchTerm: string;
}

const NodeItem: React.FC<NodeItemProps> = ({
  plugin,
  favorites,
  onDragStart,
  onToggleFavorite,
  highlightText,
  searchTerm,
}) => {
  const IconComponent = (Icons as any)[plugin.icon] || Icons.HelpCircle;
  const isFav = favorites.includes(plugin.metadata.id);

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, plugin.metadata.id)}
      className="flex items-center justify-between p-2.5 rounded-xl cursor-grab active:cursor-grabbing bg-card/35 hover:bg-secondary/40 border border-border/20 hover:border-primary/30 transition-all duration-150 group shadow-sm"
    >
      <div className="flex items-center gap-2.5 overflow-hidden">
        <div
          className="p-1.5 rounded-lg text-white shrink-0 group-hover:scale-105 transition-transform shadow-md"
          style={{ backgroundColor: plugin.color, boxShadow: `0 2px 6px ${plugin.color}33` }}
        >
          <IconComponent size={14} />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="font-bold text-xs text-foreground group-hover:text-primary transition-colors truncate">
            {highlightText(plugin.metadata.name, searchTerm)}
          </span>
          <span className="text-[10px] text-muted-foreground line-clamp-1 mt-0.5">{plugin.metadata.description}</span>
        </div>
      </div>

      <button
        onClick={(e) => onToggleFavorite(plugin.metadata.id, e)}
        className={`p-1 rounded-md hover:bg-secondary transition-colors shrink-0 ${
          isFav ? 'text-amber-400' : 'text-muted-foreground/30 hover:text-muted-foreground group-hover:opacity-100 opacity-40'
        }`}
        title={isFav ? 'Remove from favorites' : 'Add to favorites'}
      >
        <Icons.Star size={13} fill={isFav ? 'currentColor' : 'none'} />
      </button>
    </div>
  );
};

export default NodePalette;
