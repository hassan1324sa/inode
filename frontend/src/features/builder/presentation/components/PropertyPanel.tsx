import React from 'react';
import * as Icons from 'lucide-react';
import { useWorkflowProjection } from '../../application/services';
import { nodeRegistry } from '../../application/services';
import type { NodePlugin } from '../../domain/plugins/plugin';
import { CommandBus, UpdateNodePropertyCommand } from '../../application/commands/commandBus';


export const PropertyPanel: React.FC = () => {
  const { selectedNodeId, nodes } = useWorkflowProjection();
  const [plugin, setPlugin] = React.useState<NodePlugin | null>(null);

  const selectedNode = React.useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  React.useEffect(() => {
    if (selectedNode) {
      nodeRegistry.getPlugins().then((plugins) => {
        const p = plugins.get(selectedNode.type);
        if (p) setPlugin(p);
      });
    } else {
      setPlugin(null);
    }
  }, [selectedNode]);

  if (!selectedNode || !plugin) {
    return (
      <div className="flex flex-col items-center justify-center h-full border-l border-border p-4 text-xs text-muted-foreground skeuo-raised border-r-0">
        <Icons.Sliders className="mb-2 opacity-50 text-primary" size={24} />
        Select a node to configure its properties.
      </div>
    );
  }

  const handleFieldChange = (fieldName: string, value: unknown) => {
    let updates: Record<string, any> = { [fieldName]: value };
    
    // Auto-sync nested values for AI Agent
    if (selectedNode && selectedNode.type === 'ai_agent') {
      if (fieldName === 'memoryProvider') {
        const memoryObj = selectedNode.data.memory && typeof selectedNode.data.memory === 'object' ? selectedNode.data.memory : {};
        updates.memory = { ...memoryObj, provider: value };
      } else if (fieldName === 'memoryKey') {
        const memoryObj = selectedNode.data.memory && typeof selectedNode.data.memory === 'object' ? selectedNode.data.memory : {};
        updates.memory = { ...memoryObj, key: value };
      } else if (fieldName === 'enabledTools') {
        const toolNames = typeof value === 'string' ? value.split(',').map(s => s.trim()).filter(Boolean) : [];
        updates.tools = toolNames.map(name => ({ id: name, credential_id: 'default-key' }));
      } else if (fieldName === 'apiKey') {
        const modelObj = selectedNode.data.model && typeof selectedNode.data.model === 'object' ? selectedNode.data.model : {};
        updates.model = { ...modelObj, credential_id: value };
      }
    }

    CommandBus.dispatch(new UpdateNodePropertyCommand(selectedNode.id, updates));
  };

  return (
    <div className="flex flex-col h-full border-l border-border p-4 text-left overflow-y-auto skeuo-raised border-r-0">
      {/* Title Header */}
      <div className="flex items-center gap-2 pb-3 border-b border-black/40 mb-4">
        <div className="p-1.5 rounded-lg text-white shadow-inner" style={{ backgroundColor: plugin.color, boxShadow: 'inset 0 1px 1px rgba(255,255,255,0.2)' }}>
          <Icons.Settings size={14} />
        </div>
        <div>
          <h4 className="font-bold text-xs text-foreground">{plugin.metadata.name} Configurations</h4>
          <span className="text-[10px] text-muted-foreground font-mono">ID: {selectedNode.id}</span>
        </div>
      </div>

      {/* Dynamic Fields */}
      <div className="space-y-4">
        {plugin.schema.fields.map((field) => {
          let value = selectedNode.data[field.name] !== undefined ? selectedNode.data[field.name] : field.defaultValue || '';
          
          // Map nested keys for AI Agent node to keep PropertyPanel and CustomNode in sync
          if (selectedNode.type === 'ai_agent') {
            if (field.name === 'memoryProvider') {
              const memoryObj = selectedNode.data.memory && typeof selectedNode.data.memory === 'object' ? (selectedNode.data.memory as any) : {};
              value = memoryObj.provider || selectedNode.data.memoryProvider || 'conversation';
            } else if (field.name === 'memoryKey') {
              const memoryObj = selectedNode.data.memory && typeof selectedNode.data.memory === 'object' ? (selectedNode.data.memory as any) : {};
              value = memoryObj.key || selectedNode.data.memoryKey || '';
            } else if (field.name === 'enabledTools') {
              const toolsList = Array.isArray(selectedNode.data.tools) ? selectedNode.data.tools : [];
              if (toolsList.length > 0) {
                value = toolsList.map((t: any) => t.id).join(',');
              } else {
                value = selectedNode.data.enabledTools || '';
              }
            } else if (field.name === 'apiKey') {
              const modelObj = selectedNode.data.model && typeof selectedNode.data.model === 'object' ? (selectedNode.data.model as any) : {};
              value = modelObj.credential_id || selectedNode.data.apiKey || '';
            }
          }
          
          return (
            <div key={field.name} className="flex flex-col gap-1">
              <label className="text-[11px] font-bold text-foreground flex items-center justify-between">
                <span>{field.label}</span>
                {field.required && <span className="text-red-500 font-bold text-[9px]">* REQUIRED</span>}
              </label>
              
              {field.type === 'text' && (
                <input
                  type="text"
                  className="w-full rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary skeuo-sunken"
                  value={value as string}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                />
              )}

              {field.type === 'textarea' && (
                <textarea
                  rows={4}
                  className="w-full rounded-lg px-3 py-1.5 text-xs text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary resize-y skeuo-sunken"
                  value={value as string}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                />
              )}

              {field.type === 'select' && (() => {
                let stringValue = '';
                if (field.name === 'model' && selectedNode.type === 'ai_agent') {
                  stringValue = typeof value === 'object' && value ? (value as any).model || '' : (value as string);
                } else {
                  stringValue = value as string;
                }

                let selectOptions = field.options || [];
                if (field.name === 'model' && selectedNode.type === 'ai_agent' && stringValue) {
                  const hasOption = selectOptions.some(opt => opt.value === stringValue);
                  if (!hasOption) {
                    selectOptions = [...selectOptions, { label: stringValue, value: stringValue }];
                  }
                }

                return (
                  <select
                    className="w-full rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary skeuo-sunken"
                    value={stringValue}
                    onChange={(e) => {
                      if (field.name === 'model' && selectedNode.type === 'ai_agent') {
                        const modelObj = typeof value === 'object' && value ? (value as any) : {};
                        handleFieldChange(field.name, {
                          ...modelObj,
                          model: e.target.value,
                          provider: e.target.value.includes('/') ? 'openrouter' : 'google'
                        });
                      } else {
                        handleFieldChange(field.name, e.target.value);
                      }
                    }}
                  >
                    {selectOptions.map((opt) => (
                      <option key={opt.value} value={opt.value} className="bg-slate-900">
                        {opt.label}
                      </option>
                    ))}
                  </select>
                );
              })()}

              {field.type === 'switch' && (
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={!!value}
                    className="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary focus:ring-2"
                    onChange={(e) => handleFieldChange(field.name, e.target.checked)}
                  />
                  <span className="ml-2 text-xs text-muted-foreground">{field.description}</span>
                </div>
              )}

              {field.type === 'secret' && (
                <div className="relative">
                  <input
                    type="password"
                    placeholder="Enter credential ID..."
                    className="w-full rounded-lg pl-3 pr-8 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary skeuo-sunken"
                    value={value as string}
                    onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  />
                  <Icons.Key className="absolute right-2.5 top-2.5 text-muted-foreground/60" size={12} />
                </div>
              )}


              {field.description && field.type !== 'switch' && (
                <span className="text-[10px] text-muted-foreground">{field.description}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
export default PropertyPanel;
