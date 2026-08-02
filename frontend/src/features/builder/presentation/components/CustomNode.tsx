import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import * as Icons from 'lucide-react';
import { nodeRegistry } from '../../application/services';
import type { NodePlugin } from '../../domain/plugins/plugin';

export const CustomNode: React.FC<NodeProps> = ({ data, selected }) => {
  const [plugin, setPlugin] = React.useState<NodePlugin | null>(null);
  const [showTooltip, setShowTooltip] = React.useState(false);

  React.useEffect(() => {
    nodeRegistry.getPlugins().then(plugins => {
      const p = plugins.get(data.type as string);
      if (p) setPlugin(p);
    });
  }, [data.type]);

  if (!plugin) return null;

  // Resolve Icon
  const IconComponent = (Icons as any)[plugin.icon] || Icons.HelpCircle;

  // Node Validation
  const validation = plugin.validate ? plugin.validate(data) : { isValid: true, errors: [] };
  const isValid = validation.isValid;
  const errors = validation.errors || [];

  // Live Execution status from data
  const status = data.status as 'running' | 'success' | 'failed' | undefined;
  const duration = data.duration as number | undefined;

  // Visual status classes
  const ringClass = selected
    ? 'ring-2 ring-primary/60 scale-102'
    : status === 'running'
    ? 'ring-2 ring-amber-400 animate-pulse'
    : status === 'failed'
    ? 'ring-2 ring-red-500/80'
    : status === 'success'
    ? 'ring-1 ring-emerald-500/50'
    : '';

  return (
    <div
      className={`relative flex flex-col min-w-[250px] rounded-2xl transition-all duration-200 skeuo-raised skeuo-glare ${ringClass}`}
      style={{
        boxShadow: selected
          ? '0 0 15px rgba(139, 92, 246, 0.4), inset 0 1px 0px rgba(255,255,255,0.15)'
          : status === 'running'
          ? '0 0 20px rgba(245, 158, 11, 0.4), inset 0 1px 0px rgba(255,255,255,0.15)'
          : 'inset 0 1px 0px rgba(255,255,255,0.12), 0 4px 12px rgba(0,0,0,0.5)',
      }}
    >
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
            left: -7,
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
          right: -7,
        }}
      />

      {/* Header bar */}
      <div
        className="flex items-center justify-between px-6 py-4 rounded-t-2xl border-b border-black/50"
        style={{ borderTop: `4px solid ${plugin.color}` }}
      >
        <div className="flex items-center gap-3">
          <div
            className="p-2 rounded-lg text-white shadow-lg"
            style={{
              backgroundColor: plugin.color,
              boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)',
            }}
          >
            <IconComponent size={16} />
          </div>
          <div className="flex flex-col text-left">
            <span className="font-extrabold text-sm text-foreground skeuo-embossed">
              {String(data.label || plugin.metadata.name)}
            </span>
            <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase">
              {plugin.metadata.category}
            </span>
          </div>
        </div>

        {/* Status / Validation Badges */}
        <div className="flex items-center gap-1.5 z-20">
          {status === 'running' && (
            <span title="Running...">
              <Icons.Loader2 size={16} className="text-amber-400 animate-spin" />
            </span>
          )}
          {status === 'success' && (
            <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/30 font-mono">
              <Icons.CheckCircle2 size={12} />
              {duration ? `${duration}ms` : 'OK'}
            </span>
          )}
          {status === 'failed' && (
            <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-red-950/80 text-red-300 border border-red-500/30 font-mono">
              <Icons.AlertCircle size={12} />
              ERR
            </span>
          )}

          {/* Validation Warning badge with hover tooltip */}
          {!isValid && (
            <div
              className="relative cursor-pointer"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
            >
              <div className="p-1 rounded-full bg-red-950/90 text-red-400 border border-red-500/40 animate-pulse">
                <Icons.AlertTriangle size={13} />
              </div>

              {showTooltip && (
                <div className="absolute right-0 top-6 w-48 p-2 rounded-lg bg-black/95 text-white text-[11px] border border-red-500/40 shadow-2xl z-50">
                  <div className="font-bold text-red-400 mb-1 flex items-center gap-1">
                    <Icons.AlertTriangle size={12} />
                    <span>Configuration Error</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-red-200/90">
                    {errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
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
            <div className="text-[10px] text-muted-foreground mt-1 truncate">
              Value: {String(data.variable_value || '')}
            </div>
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
            <p className="text-muted-foreground text-[10px] truncate italic">
              "{String(data.prompt || '')}"
            </p>
          </div>
        )}
        {plugin.metadata.id === 'webhook_trigger' && (
          <div className="text-xs">
            <span className="font-bold text-emerald-400 mr-1.5">{String(data.method || 'POST')}</span>
            <span className="text-muted-foreground font-mono">{String(data.path || '/webhook')}</span>
          </div>
        )}
        {plugin.metadata.id === 'slack_notification' && (
          <div className="text-xs flex flex-col gap-0.5">
            <span className="text-pink-400 font-mono text-[10px]">{String(data.channel || '#general')}</span>
            <p className="text-muted-foreground text-[10px] truncate">{String(data.message || '')}</p>
          </div>
        )}
        {plugin.metadata.id === 'if_condition' && (
          <div className="text-xs">
            <code className="text-amber-300 font-mono text-[10px] bg-amber-950/30 px-1 py-0.5 rounded">
              {String(data.expression || 'true')}
            </code>
          </div>
        )}
        {plugin.metadata.id === 'delay_timer' && (
          <div className="text-xs text-muted-foreground">
            Wait <span className="text-foreground font-bold">{String(data.durationSeconds || '5')}</span> seconds
          </div>
        )}
      </div>
    </div>
  );
};
export default CustomNode;

