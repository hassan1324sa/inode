import React from 'react';
import * as Icons from 'lucide-react';
import { SearchNodesHandler, SearchNodesQuery } from '../../application/queries/searchNodes';
import type { NodePlugin } from '../../domain/plugins/plugin';


interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, nodeType: string) => void;
}

export const NodePalette: React.FC<NodePaletteProps> = ({ onDragStart }) => {
  const [searchTerm, setSearchTerm] = React.useState('');
  const [plugins, setPlugins] = React.useState<NodePlugin[]>([]);
  
  const searchHandler = React.useMemo(() => new SearchNodesHandler(), []);

  React.useEffect(() => {
    searchHandler.execute(new SearchNodesQuery(searchTerm)).then(setPlugins);
  }, [searchTerm, searchHandler]);

  return (
    <div className="flex flex-col h-full border-r border-border glass p-4">
      {/* Title */}
      <div className="flex items-center gap-2 mb-4">
        <Icons.PlusSquare className="text-primary" size={20} />
        <h3 className="font-bold text-sm text-foreground">Add Nodes</h3>
      </div>

      {/* Search Input */}
      <div className="relative mb-4">
        <Icons.Search className="absolute left-3 top-2.5 text-muted-foreground" size={16} />
        <input
          type="text"
          placeholder="Search nodes (e.g. api, llm)..."
          className="w-full pl-9 pr-4 py-1.5 bg-background/50 border border-border rounded-md text-xs focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary text-foreground"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Nodes List */}
      <div className="flex-1 overflow-y-auto space-y-2.5">
        {plugins.map((plugin) => {
          const IconComponent = (Icons as any)[plugin.icon] || Icons.HelpCircle;
          return (
            <div
              key={plugin.metadata.id}
              draggable
              onDragStart={(e) => onDragStart(e, plugin.metadata.id)}
              className="flex items-center gap-3 p-3 rounded-lg border border-border bg-background/20 hover:bg-background/40 hover:border-primary/50 cursor-grab active:cursor-grabbing transition-all duration-150 group"
            >
              <div className="p-1.5 rounded text-white group-hover:scale-105 transition-transform" style={{ backgroundColor: plugin.color }}>
                <IconComponent size={14} />
              </div>
              <div className="flex flex-col text-left">
                <span className="font-semibold text-xs text-foreground">{plugin.metadata.name}</span>
                <span className="text-[10px] text-muted-foreground line-clamp-1">{plugin.metadata.description}</span>
              </div>
            </div>
          );
        })}
        {plugins.length === 0 && (
          <div className="text-center py-8 text-xs text-muted-foreground">No nodes found.</div>
        )}
      </div>
    </div>
  );
};
export default NodePalette;
