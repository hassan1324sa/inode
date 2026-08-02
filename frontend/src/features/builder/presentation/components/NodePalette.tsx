import React from 'react';
import * as Icons from 'lucide-react';
import { SearchNodesHandler, SearchNodesQuery } from '../../application/queries/searchNodes';
import type { NodePlugin } from '../../domain/plugins/plugin';

interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, nodeType: string) => void;
  onOpenPackageBrowser?: () => void;
}

const CATEGORIES = [
  'All', 'Favorites', 'Recent',
  'AI', 'Triggers', 'HTTP', 'Communication',
  'Logic', 'Variables', 'Data', 'Files', 'Utilities', 'Installed Packages'
];

export const NodePalette: React.FC<NodePaletteProps> = ({ onDragStart, onOpenPackageBrowser }) => {
  const [searchTerm, setSearchTerm] = React.useState('');
  const [plugins, setPlugins] = React.useState<NodePlugin[]>([]);
  const [selectedCategory, setSelectedCategory] = React.useState('All');
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
    // Record in recently used
    setRecent((prev) => {
      const filtered = prev.filter((item) => item !== id);
      const next = [id, ...filtered].slice(0, 8);
      localStorage.setItem('fluxa_recent_nodes', JSON.stringify(next));
      return next;
    });
    onDragStart(e, id);
  };

  const filteredPlugins = React.useMemo(() => {
    return plugins.filter((plugin) => {
      if (selectedCategory === 'All') return true;
      if (selectedCategory === 'Favorites') return favorites.includes(plugin.metadata.id);
      if (selectedCategory === 'Recent') return recent.includes(plugin.metadata.id);
      return plugin.metadata.category === selectedCategory;
    });
  }, [plugins, selectedCategory, favorites, recent]);

  return (
    <div className="flex flex-col h-full border-r border-border p-3.5 skeuo-raised border-l-0 text-left overflow-hidden">
      {/* Title Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icons.PlusSquare className="text-primary" size={18} />
          <h3 className="font-bold text-sm text-foreground">Node Palette</h3>
        </div>
        {onOpenPackageBrowser && (
          <button
            onClick={onOpenPackageBrowser}
            className="text-[10px] flex items-center gap-1 px-2 py-1 rounded bg-secondary hover:bg-muted text-muted-foreground hover:text-foreground transition-colors border border-border"
            title="Browse Packages"
          >
            <Icons.Package size={12} />
            <span>Packages</span>
          </button>
        )}
      </div>

      {/* Search Bar */}
      <div className="relative mb-3">
        <Icons.Search className="absolute left-3 top-2.5 text-muted-foreground" size={14} />
        <input
          type="text"
          placeholder="Search nodes..."
          className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground skeuo-sunken"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Category Pills Slider */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 mb-2 scrollbar-none">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-2.5 py-1 rounded-full text-[10px] font-bold whitespace-nowrap transition-all border ${
              selectedCategory === cat
                ? 'bg-primary text-white border-primary shadow-sm'
                : 'bg-secondary/60 text-muted-foreground border-border/40 hover:text-foreground hover:bg-secondary'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Nodes List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
        {filteredPlugins.map((plugin) => {
          const IconComponent = (Icons as any)[plugin.icon] || Icons.HelpCircle;
          const isFav = favorites.includes(plugin.metadata.id);
          return (
            <div
              key={plugin.metadata.id}
              draggable
              onDragStart={(e) => handleDragStart(e, plugin.metadata.id)}
              className="flex items-center justify-between p-2.5 rounded-xl cursor-grab active:cursor-grabbing transition-all duration-150 group skeuo-raised hover:border-primary/50"
            >
              <div className="flex items-center gap-2.5 overflow-hidden">
                <div
                  className="p-1.5 rounded-lg text-white shrink-0 group-hover:scale-105 transition-transform shadow-sm"
                  style={{ backgroundColor: plugin.color }}
                >
                  <IconComponent size={14} />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-bold text-xs text-foreground truncate">{plugin.metadata.name}</span>
                  <span className="text-[10px] text-muted-foreground line-clamp-1">{plugin.metadata.description}</span>
                </div>
              </div>

              {/* Favorite toggle button */}
              <button
                onClick={(e) => toggleFavorite(plugin.metadata.id, e)}
                className={`p-1 rounded hover:bg-white/10 transition-colors shrink-0 ${
                  isFav ? 'text-amber-400' : 'text-muted-foreground/30 hover:text-muted-foreground'
                }`}
                title={isFav ? 'Remove from favorites' : 'Add to favorites'}
              >
                <Icons.Star size={13} fill={isFav ? 'currentColor' : 'none'} />
              </button>
            </div>
          );
        })}

        {filteredPlugins.length === 0 && (
          <div className="text-center py-8 text-xs text-muted-foreground">
            No nodes found in "{selectedCategory}".
          </div>
        )}
      </div>
    </div>
  );
};
export default NodePalette;

