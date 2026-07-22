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
    <div className={`relative flex flex-col min-w-[250px] rounded-2xl transition-all duration-200 skeuo-raised skeuo-glare ${
      selected ? 'ring-2 ring-primary/60 scale-102' : ''
    }`} style={{ boxShadow: selected ? '0 0 15px rgba(139, 92, 246, 0.4), inset 0 1px 0px rgba(255,255,255,0.15)' : 'inset 0 1px 0px rgba(255,255,255,0.12), 0 4px 12px rgba(0,0,0,0.5)' }}>
      {/* Decorative Corner Screws */}
      <div className="absolute top-2 left-2 skeuo-screw z-10" />
      <div className="absolute top-2 right-2 skeuo-screw z-10" />
      <div className="absolute bottom-2 left-2 skeuo-screw z-10" />
      <div className="absolute bottom-2 right-2 skeuo-screw z-10" />

      {/* Handles styled as physical port jacks */}
      {!plugin.capabilities.trigger && (
        <Handle
          type="target"
          position={Position.Left}
          style={{
            background: 'hsl(var(--input))',
            border: '2.5px solid #7f8c8d',
            boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.9), 0 1px 1px rgba(255,255,255,0.1)',
            width: 14,
            height: 14,
            left: -7
          }}
        />
      )}
      
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: 'hsl(var(--input))',
          border: '2.5px solid #7f8c8d',
          boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.9), 0 1px 1px rgba(255,255,255,0.1)',
          width: 14,
          height: 14,
          right: -7
        }}
      />

      {/* Header bar */}
      <div className="flex items-center gap-3 px-6 py-4 rounded-t-2xl border-b border-black/50" style={{ borderTop: `4px solid ${plugin.color}` }}>
        <div className="p-2 rounded-lg text-white shadow-lg" style={{ backgroundColor: plugin.color, boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)' }}>
          <IconComponent size={16} />
        </div>
        <div className="flex flex-col text-left">
          <span className="font-extrabold text-sm text-foreground skeuo-embossed">{plugin.metadata.name}</span>
          <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase">{plugin.metadata.category}</span>

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
