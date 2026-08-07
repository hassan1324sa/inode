import React from 'react';
import * as Icons from 'lucide-react';
import { useUIProjection, useWorkflowProjection } from '../../application/services';
import { CommandBus, DeleteSelectionCommand } from '../../application/commands/commandBus';

interface CommandPaletteProps {
  onRunWorkflow?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ onRunWorkflow }) => {
  const { commandPaletteOpen, setCommandPaletteOpen } = useUIProjection();
  const [query, setQuery] = React.useState('');
  const { nodes, edges } = useWorkflowProjection();


  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCtrlK = (e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'k' || e.code === 'KeyK');
      const isAltK = e.altKey && (e.key.toLowerCase() === 'k' || e.code === 'KeyK');
      const isCtrlSlash = (e.ctrlKey || e.metaKey) && (e.key === '/' || e.code === 'Slash');

      if (isCtrlK || isAltK || isCtrlSlash) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        setCommandPaletteOpen(!useUIProjection.getState().commandPaletteOpen);
      }
      if (e.key === 'Escape' || e.code === 'Escape') {
        if (useUIProjection.getState().commandPaletteOpen) {
          setCommandPaletteOpen(false);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, [setCommandPaletteOpen]);

  if (!commandPaletteOpen) return null;

  const handleClearCanvas = () => {
    const nodeIds = nodes.map(n => n.id);
    const edgeIds = edges.map(e => e.id);
    if (nodeIds.length > 0 || edgeIds.length > 0) {
      CommandBus.dispatch(new DeleteSelectionCommand(nodeIds, edgeIds));
    }
  };

  const actions = [
    { name: 'Run Workflow', desc: 'Trigger manual backend execution', icon: 'Play', action: () => onRunWorkflow?.() },
    { name: 'Undo Last Action', desc: 'Revert last canvas command', icon: 'Undo', action: () => CommandBus.undo() },
    { name: 'Redo Action', desc: 'Reapply last undone canvas command', icon: 'Redo', action: () => CommandBus.redo() },
    { name: 'Clear Canvas', desc: 'Delete all nodes and edges', icon: 'Trash2', action: handleClearCanvas },
  ];

  const filteredActions = actions.filter(
    (act) =>
      act.name.toLowerCase().includes(query.toLowerCase()) ||
      act.desc.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div
      className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-start justify-center pt-24"
      onClick={() => setCommandPaletteOpen(false)}
    >
      <div
        className="w-[500px] bg-card text-card-foreground border border-border rounded-lg shadow-2xl overflow-hidden text-left flex flex-col glass"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50">
          <Icons.Search className="text-muted-foreground" size={18} />
          <input
            type="text"
            placeholder="Type a command or search nodes..."
            className="flex-1 bg-transparent border-none text-sm text-foreground focus:outline-none focus:ring-0"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <span className="text-[10px] bg-muted/50 px-2 py-0.5 rounded text-muted-foreground font-mono">ESC</span>
        </div>

        {/* Action List */}
        <div className="max-h-[300px] overflow-y-auto p-2 space-y-1">
          <div className="text-[10px] font-bold text-muted-foreground px-3 py-1 uppercase">Commands</div>
          {filteredActions.map((act) => {
            const Icon = (Icons as any)[act.icon] || Icons.Terminal;
            return (
              <button
                key={act.name}
                onClick={() => {
                  act.action();
                  setCommandPaletteOpen(false);
                }}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-primary/20 text-left transition-colors duration-100 group"
              >
                <div className="p-1 rounded bg-muted text-muted-foreground group-hover:bg-primary group-hover:text-white transition-colors">
                  <Icon size={14} />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-foreground">{act.name}</span>
                  <span className="text-[10px] text-muted-foreground">{act.desc}</span>
                </div>
              </button>
            );
          })}
          {filteredActions.length === 0 && (
            <div className="text-center py-6 text-xs text-muted-foreground">No matching commands found.</div>
          )}
        </div>
      </div>
    </div>
  );
};
export default CommandPalette;
