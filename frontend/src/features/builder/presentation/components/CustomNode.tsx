import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import * as Icons from 'lucide-react';
import { nodeRegistry } from '../../application/services';
import type { NodePlugin } from '../../domain/plugins/plugin';

export const CustomNode: React.FC<NodeProps> = ({ data, selected }) => {

  const [plugin, setPlugin] = React.useState<NodePlugin | null>(null);

  React.useEffect(() => {
    nodeRegistry.getPlugins().then(plugins => {
      const p = plugins.get(data.type as string);
      if (p) setPlugin(p);
    });
  }, [data.type]);

  if (!plugin) return null;

  // Resolve Icon
  const IconComponent = (Icons as any)[plugin.icon] || Icons.HelpCircle;

  return (
    <div className={`relative flex flex-col min-w-[240px] rounded-lg shadow-lg border transition-all duration-200 glass ${
      selected ? 'border-primary shadow-primary/20 ring-2 ring-primary/20 scale-102' : 'border-border'
    }`}>
      {/* Handles */}
      {!plugin.capabilities.trigger && (
        <Handle
          type="target"
          position={Position.Left}
          style={{ background: 'hsl(var(--primary))', width: 8, height: 8 }}
        />
      )}
      
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: 'hsl(var(--primary))', width: 8, height: 8 }}
      />

      {/* Header bar */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-t-lg border-b border-border/50" style={{ borderTop: `4px solid ${plugin.color}` }}>
        <div className="p-1.5 rounded-md text-white" style={{ backgroundColor: plugin.color }}>
          <IconComponent size={16} />
        </div>
        <div className="flex flex-col text-left">
          <span className="font-semibold text-sm text-foreground">{plugin.metadata.name}</span>
          <span className="text-xs text-muted-foreground">{plugin.metadata.category}</span>
        </div>
      </div>

      {/* Body preview */}
      <div className="px-4 py-3 text-left flex flex-col gap-1.5 bg-background/30 rounded-b-lg">
        {plugin.metadata.id === 'set_variable' && (
          <div className="text-xs">
            <span className="text-muted-foreground">Var: </span>
            <code className="text-primary-foreground font-mono bg-muted/40 px-1 py-0.5 rounded">
              {String(data.variable_name || '')}
            </code>
            <div className="text-[10px] text-muted-foreground mt-1 truncate">Value: {String(data.variable_value || '')}</div>
          </div>
        )}
        {plugin.metadata.id === 'http_request' && (
          <div className="text-xs">
            <span className="font-bold text-blue-400 mr-1.5">{String(data.method || 'GET')}</span>
            <span className="text-muted-foreground font-mono break-all">{String(data.url || '')}</span>
          </div>
        )}
        {plugin.metadata.id === 'ai_agent' && (
          <div className="text-xs flex flex-col gap-1">
            <span className="text-emerald-400 font-medium text-[10px]">{String(data.model || '')}</span>
            <p className="text-muted-foreground text-[10px] truncate italic">"{String(data.prompt || '')}"</p>
          </div>
        )}
      </div>
    </div>
  );
};
export default CustomNode;
