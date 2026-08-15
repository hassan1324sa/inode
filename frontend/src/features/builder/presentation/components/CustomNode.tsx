import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import * as Icons from 'lucide-react';
import { nodeRegistry, useWorkflowProjection, useExecutionProjection } from '../../application/services';
import type { NodePlugin } from '../../domain/plugins/plugin';
import { CommandBus, UpdateNodePropertyCommand } from '../../application/commands/commandBus';
import { authenticatedFetch } from '../../../../shared/api/authenticatedFetch';

export const CustomNode: React.FC<NodeProps> = ({ id, data, selected }) => {
  const [plugin, setPlugin] = React.useState<NodePlugin | null>(null);
  const [showTooltip, setShowTooltip] = React.useState(false);

  // States for Agent builder
  const { } = useWorkflowProjection();
  const [activeConfigTab, setActiveConfigTab] = React.useState<'chat_model' | 'memory' | 'tool' | null>(null);
  const [catalog, setCatalog] = React.useState<{ providers: any[]; models: Record<string, any[]> } | null>(null);
  const [credentialsList, setCredentialsList] = React.useState<{ credential_id: string }[]>([]);
  const [showAddCredential, setShowAddCredential] = React.useState(false);
  const [newCredName, setNewCredName] = React.useState('');
  const [newCredVal, setNewCredVal] = React.useState('');
  const [allPlugins, setAllPlugins] = React.useState<any[]>([]);
  const [selectedToolConfigId, setSelectedToolConfigId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (data.type === 'ai_agent') {
      // Fetch models catalog from backend API
      authenticatedFetch('/api/v1/debug/models')
        .then(res => res.json())
        .then(data => {
          if (data && data.providers && data.models) {
            setCatalog(data);
          } else {
            console.error('Invalid models response:', data);
          }
        })
        .catch(err => console.error(err));
        
      // Fetch credentials from backend API
      authenticatedFetch('/api/v1/debug/credentials')
        .then(res => res.json())
        .then(data => {
          if (data && data.credentials) {
            setCredentialsList(data.credentials);
          }
        })
        .catch(err => console.error(err));

      // Fetch tool plugins
      nodeRegistry.getPlugins().then(pluginsMap => {
        const list: any[] = [];
        pluginsMap.forEach((p) => {
          if (p.capabilities && (p.capabilities as any).supports_agent_tool) {
            list.push(p);
          }
        });
        setAllPlugins(list);
      });
    }
  }, [data.type]);

  // Live Execution status dynamically loaded from EventBus and Execution Projection
  const activeExecutionId = useExecutionProjection((state: any) => state.activeExecutionId);
  const activeSnapshot = useExecutionProjection((state: any) => 
    activeExecutionId ? state.snapshots[activeExecutionId] : null
  );

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

  let status = data.status as 'running' | 'success' | 'failed' | undefined;
  let duration = data.duration as number | undefined;

  if (activeSnapshot) {
    // If there is an active execution running
    if (activeSnapshot.completedNodes.includes(id)) {
      status = 'success';
    } else if (activeSnapshot.status === 'Running' && !activeSnapshot.completedNodes.includes(id)) {
      // If the workflow is running and this node is next or currently active
      // In eventBus, progress/logs tell us. Let's make it show running if it is the current execution trace last log or in progress
      const latestLog = activeSnapshot.logs[activeSnapshot.logs.length - 1] || '';
      if (latestLog.includes(id) || latestLog.includes((data.label as string) || '')) {
        status = 'running';
      } else if (activeSnapshot.logs.some((l: string) => l.includes(`Step ${id} started`)) && !activeSnapshot.completedNodes.includes(id)) {
        status = 'running';
      }
    }
    
    // Check if the workflow failed on this node
    if (activeSnapshot.status === 'Failed') {
      const latestLog = activeSnapshot.logs[activeSnapshot.logs.length - 1] || '';
      if (latestLog.includes('failed') && (latestLog.includes(id) || latestLog.includes(data.label || ''))) {
        status = 'failed';
      }
    }
  }

  // Visual status classes
  const ringClass = selected
    ? 'ring-2 ring-primary/60 scale-102'
    : status === 'running'
    ? 'ring-2 ring-amber-400 animate-pulse'
    : status === 'failed'
    ? 'ring-2 ring-red-500/80 shadow-[0_0_15px_rgba(239,68,68,0.5)]'
    : status === 'success'
    ? 'ring-2 ring-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.4)]'
    : '';

  return (
    <div
      className={`relative flex flex-col w-[280px] rounded-xl transition-all duration-200 bg-slate-900/90 border border-slate-700/80 backdrop-blur-md text-foreground ${ringClass}`}
      style={{
        boxShadow: selected
          ? '0 0 20px rgba(139, 92, 246, 0.25), 0 4px 12px rgba(0,0,0,0.5)'
          : '0 4px 12px rgba(0,0,0,0.4)',
      }}
    >

      {/* Handles styled as physical port jacks */}
      {!plugin.capabilities.trigger && (
        <Handle
          type="target"
          position={Position.Left}
          style={{
            background: 'hsl(var(--background))',
            border: '2px solid hsl(var(--border))',
            width: 12,
            height: 12,
            left: -6,
          }}
        />
      )}

      {/* If it's a conditional node, render True (top) and False (bottom) source handles on the right */}
      {plugin.metadata.id === 'if_condition' ? (
        <>
          <Handle
            type="source"
            id="true"
            position={Position.Right}
            style={{
              background: '#10b981', // emerald green for True
              border: '2px solid #047857',
              width: 12,
              height: 12,
              right: -6,
              top: '30%',
            }}
          />
          <Handle
            type="source"
            id="false"
            position={Position.Right}
            style={{
              background: '#ef4444', // red for False
              border: '2px solid #b91c1c',
              width: 12,
              height: 12,
              right: -6,
              top: '70%',
            }}
          />
        </>
      ) : (
        <>
          <Handle
            type="source"
            position={Position.Right}
            style={{
              background: 'hsl(var(--background))',
              border: '2px solid hsl(var(--border))',
              width: 12,
              height: 12,
              right: -6,
            }}
          />
          {plugin.metadata.id === 'ai_agent' && (
            <>
              {/* Bottom handles are defined in the dedicated bottom bar */}
            </>
          )}
        </>
      )}

      {/* Header bar */}
      <div
        className="flex items-center justify-between px-4 py-3.5 rounded-t-xl border-b border-slate-800"
        style={{ borderTop: `3px solid ${plugin.color}` }}
      >
        <div className="flex items-center gap-3">
          <div
            className="p-1.5 rounded-lg text-white"
            style={{
              backgroundColor: plugin.color,
            }}
          >
            <IconComponent size={14} />
          </div>
          <div className="flex flex-col text-left">
            <span className="font-semibold text-xs text-slate-100">
              {String(data.label || plugin.metadata.name)}
            </span>
            <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-wider">
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
      <div className={`px-4 py-3 text-left flex flex-col gap-1.5 bg-background/30 ${plugin.metadata.id === 'ai_agent' ? '' : 'rounded-b-lg'}`}>
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
        {plugin.metadata.id === 'ai_agent' && (() => {
          const modelObj = data.model && typeof data.model === 'object' ? (data.model as any) : {};
          const memoryObj = data.memory && typeof data.memory === 'object' ? (data.memory as any) : {};
          const toolsList = Array.isArray(data.tools) ? data.tools : [];

          const updateModel = (fields: any) => {
            CommandBus.dispatch(new UpdateNodePropertyCommand(id, {
              model: {
                ...modelObj,
                ...fields
              }
            }));
          };

          const updateMemory = (fields: any) => {
            CommandBus.dispatch(new UpdateNodePropertyCommand(id, {
              memory: {
                ...memoryObj,
                ...fields
              }
            }));
          };

          const handleAddCredential = () => {
            if (!newCredName || !newCredVal) return;
            authenticatedFetch('/api/v1/debug/credentials', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                name: newCredName,
                provider: modelObj.provider || 'google',
                value: newCredVal
              })
            })
              .then(res => res.json())
              .then(resData => {
                setCredentialsList(prev => [...prev, { credential_id: resData.credential_id }]);
                updateModel({ credential_id: resData.credential_id });
                setNewCredName('');
                setNewCredVal('');
                setShowAddCredential(false);
              })
              .catch(err => console.error(err));
          };

          return (
            <div className="text-xs flex flex-col gap-2.5">
              <div className="flex flex-col gap-0.5">
                <span className="text-emerald-400 font-medium text-[10px]">
                  Model: {modelObj.provider ? `${modelObj.provider.toUpperCase()} / ` : ''}{modelObj.model || 'gemini-1.5-flash'}
                </span>
                {modelObj.credential_id && (
                  <span className="text-[9px] text-slate-400 font-mono">
                    Credential: {modelObj.credential_id}
                  </span>
                )}
                <p className="text-muted-foreground text-[10px] truncate italic mt-1">
                  "{String(data.prompt || 'Summarize the input')}"
                </p>
              </div>

              {/* Toggles */}
              <div className="flex justify-between gap-1.5 mt-1 z-20">
                <button
                  onClick={(e) => { e.stopPropagation(); setActiveConfigTab(activeConfigTab === 'chat_model' ? null : 'chat_model'); }}
                  className={`flex-1 text-[9px] font-semibold py-1 px-1 rounded border transition-all duration-150 flex items-center justify-center gap-1 ${
                    activeConfigTab === 'chat_model'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 shadow-[0_0_8px_rgba(16,185,129,0.3)]'
                      : 'bg-slate-800/60 text-slate-300 border-slate-700/60 hover:bg-slate-800 hover:text-emerald-400'
                  }`}
                >
                  <Icons.Cpu size={10} />
                  <span>Model</span>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setActiveConfigTab(activeConfigTab === 'memory' ? null : 'memory'); }}
                  className={`flex-1 text-[9px] font-semibold py-1 px-1 rounded border transition-all duration-150 flex items-center justify-center gap-1 ${
                    activeConfigTab === 'memory'
                      ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/50 shadow-[0_0_8px_rgba(99,102,241,0.3)]'
                      : 'bg-slate-800/60 text-slate-300 border-slate-700/60 hover:bg-slate-800 hover:text-indigo-400'
                  }`}
                >
                  <Icons.Database size={10} />
                  <span>Memory</span>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setActiveConfigTab(activeConfigTab === 'tool' ? null : 'tool'); }}
                  className={`flex-1 text-[9px] font-semibold py-1 px-1 rounded border transition-all duration-150 flex items-center justify-center gap-1 ${
                    activeConfigTab === 'tool'
                      ? 'bg-pink-500/20 text-pink-300 border-pink-500/50 shadow-[0_0_8px_rgba(236,72,153,0.3)]'
                      : 'bg-slate-800/60 text-slate-300 border-slate-700/60 hover:bg-slate-800 hover:text-pink-400'
                  }`}
                >
                  <Icons.Wrench size={10} />
                  <span>Tools</span>
                </button>
              </div>

              {/* Expansions */}
              {activeConfigTab && (
                <div className="mt-1 p-2.5 rounded-lg bg-slate-950/90 border border-slate-850 text-xs flex flex-col gap-2.5 z-30 shadow-2xl">
                  {activeConfigTab === 'chat_model' && (
                    <>
                      <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                        <span className="font-bold text-[10px] text-emerald-400 flex items-center gap-1">
                          <Icons.Cpu size={12} /> Chat Model Setup
                        </span>
                        <button onClick={() => setActiveConfigTab(null)} className="text-slate-500 hover:text-slate-300">
                          <Icons.X size={12} />
                        </button>
                      </div>

                      <div className="flex flex-col gap-1">
                        <label className="text-[9px] font-bold text-slate-400">PROVIDER</label>
                        <select
                          className="w-full bg-slate-900 border border-slate-700/60 rounded px-2 py-1 text-[10px] text-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500"
                          value={String(modelObj.provider || 'google')}
                          onChange={(e) => updateModel({ provider: e.target.value, model: catalog?.models[e.target.value]?.[0]?.id || '' })}
                        >
                          {catalog?.providers?.map((p: any) => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          )) || (
                            <>
                              <option value="google">Google Gemini</option>
                              <option value="openai">OpenAI</option>
                              <option value="anthropic">Anthropic</option>
                              <option value="openrouter">OpenRouter</option>
                            </>
                          )}
                        </select>
                      </div>

                      <div className="flex flex-col gap-1">
                        <label className="text-[9px] font-bold text-slate-400">MODEL</label>
                        <input
                          list="model-options"
                          type="text"
                          placeholder="Type or select model..."
                          className="w-full bg-slate-900 border border-slate-700/60 rounded px-2 py-1 text-[10px] text-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500"
                          value={String(modelObj.model || '')}
                          onChange={(e) => updateModel({ model: e.target.value })}
                        />
                        <datalist id="model-options">
                          {((catalog?.models && catalog.models[modelObj.provider || 'google']) || []).map((m: any) => (
                            <option key={m.id} value={m.id}>
                              {m.name}
                            </option>
                          ))}
                        </datalist>
                      </div>

                      <div className="flex flex-col gap-1">
                        <div className="flex justify-between items-center">
                          <label className="text-[9px] font-bold text-slate-400">CREDENTIAL REFERENCE</label>
                          <button
                            onClick={() => setShowAddCredential(!showAddCredential)}
                            className="text-[9px] text-primary hover:underline font-bold"
                          >
                            {showAddCredential ? 'Cancel' : '+ Add New'}
                          </button>
                        </div>

                        {!showAddCredential ? (
                          <select
                            className="w-full bg-slate-900 border border-slate-700/60 rounded px-2 py-1 text-[10px] text-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500"
                            value={String(modelObj.credential_id || '')}
                            onChange={(e) => updateModel({ credential_id: e.target.value })}
                          >
                            <option value="">Select credential...</option>
                            {credentialsList.map((c) => (
                              <option key={c.credential_id} value={c.credential_id}>{c.credential_id}</option>
                            ))}
                          </select>
                        ) : (
                          <div className="mt-1 p-2 rounded border border-slate-800 bg-slate-900/60 flex flex-col gap-2">
                            <input
                              type="text"
                              placeholder="Credential Name (e.g. google-key)"
                              className="w-full bg-slate-950 border border-slate-700/50 rounded px-2 py-1 text-[10px] text-foreground focus:outline-none"
                              value={newCredName}
                              onChange={(e) => setNewCredName(e.target.value)}
                            />
                            <input
                              type="password"
                              placeholder="API Key Secret Value"
                              className="w-full bg-slate-950 border border-slate-700/50 rounded px-2 py-1 text-[10px] text-foreground focus:outline-none"
                              value={newCredVal}
                              onChange={(e) => setNewCredVal(e.target.value)}
                            />
                            <button
                              onClick={handleAddCredential}
                              className="w-full py-1 bg-primary text-white text-[9px] font-bold rounded"
                            >
                              Save Credential to Vault
                            </button>
                          </div>
                        )}
                      </div>
                    </>
                  )}

                  {activeConfigTab === 'memory' && (
                    <>
                      <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                        <span className="font-bold text-[10px] text-indigo-400 flex items-center gap-1">
                          <Icons.Database size={12} /> Agent Memory Layer
                        </span>
                        <button onClick={() => setActiveConfigTab(null)} className="text-slate-500 hover:text-slate-300">
                          <Icons.X size={12} />
                        </button>
                      </div>

                      <div className="flex flex-col gap-1">
                        <label className="text-[9px] font-bold text-slate-400">PROVIDER</label>
                        <select
                          className="w-full bg-slate-900 border border-slate-700/60 rounded px-2 py-1 text-[10px] text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-500"
                          value={String(memoryObj.provider || 'conversation')}
                          onChange={(e) => updateMemory({ provider: e.target.value })}
                        >
                          <option value="none">None</option>
                          <option value="conversation">Conversation Memory (Chroma)</option>
                          <option value="postgres">PostgreSQL Memory</option>
                          <option value="redis">Redis Cache Memory</option>
                        </select>
                      </div>

                      <div className="flex flex-col gap-1">
                        <label className="text-[9px] font-bold text-slate-400">MEMORY DYNAMIC KEY</label>
                        <input
                          type="text"
                          placeholder="e.g. customer_{{email}}"
                          className="w-full bg-slate-900 border border-slate-700/60 rounded px-2 py-1 text-[10px] text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-500"
                          value={String(memoryObj.key || '')}
                          onChange={(e) => updateMemory({ key: e.target.value })}
                        />
                      </div>

                      <div className="flex gap-2">
                        <div className="flex-1 flex flex-col gap-1">
                          <label className="text-[9px] font-bold text-slate-400">SCOPE</label>
                          <select
                            className="w-full bg-slate-900 border border-slate-700/60 rounded px-1.5 py-1 text-[10px] text-foreground focus:outline-none"
                            value={String(memoryObj.scope || 'workflow')}
                            onChange={(e) => updateMemory({ scope: e.target.value })}
                          >
                            <option value="workflow">Workflow</option>
                            <option value="execution">Execution</option>
                          </select>
                        </div>
                        <div className="flex-1 flex flex-col gap-1">
                          <label className="text-[9px] font-bold text-slate-400">RETENTION</label>
                          <select
                            className="w-full bg-slate-900 border border-slate-700/60 rounded px-1.5 py-1 text-[10px] text-foreground focus:outline-none"
                            value={String(memoryObj.retention || 'persistent')}
                            onChange={(e) => updateMemory({ retention: e.target.value })}
                          >
                            <option value="persistent">Persistent</option>
                            <option value="ephemeral">Ephemeral</option>
                          </select>
                        </div>
                      </div>
                    </>
                  )}

                  {activeConfigTab === 'tool' && (
                    <>
                      <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                        <span className="font-bold text-[10px] text-pink-400 flex items-center gap-1">
                          <Icons.Wrench size={12} /> Registered Tools
                        </span>
                        <button onClick={() => setActiveConfigTab(null)} className="text-slate-500 hover:text-slate-300">
                          <Icons.X size={12} />
                        </button>
                      </div>

                      <div className="flex flex-col gap-2 max-h-[160px] overflow-y-auto pr-1">
                        <label className="text-[9px] font-bold text-slate-400 mb-0.5">SELECT ENABLED TOOLS</label>
                        {allPlugins.map((tool) => {
                          const isEnabled = toolsList.some((t: any) => t.id === tool.metadata.id);
                          const toolConfig = toolsList.find((t: any) => t.id === tool.metadata.id) || {};
                          
                          const toggleTool = () => {
                            let nextTools: any[];
                            if (isEnabled) {
                              nextTools = toolsList.filter((t: any) => t.id !== tool.metadata.id);
                              if (selectedToolConfigId === tool.metadata.id) {
                                setSelectedToolConfigId(null);
                              }
                            } else {
                              nextTools = [...toolsList, { id: tool.metadata.id, credential_id: 'default-key' }];
                            }
                            CommandBus.dispatch(new UpdateNodePropertyCommand(id, { tools: nextTools }));
                          };

                          const ToolIcon = (Icons as any)[tool.icon] || Icons.Wrench;

                          return (
                            <div key={tool.metadata.id} className="flex flex-col gap-1.5 p-2 rounded bg-slate-900 border border-slate-800">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1.5 cursor-pointer text-[10px]" onClick={toggleTool}>
                                  <ToolIcon size={11} className={isEnabled ? 'text-pink-400' : 'text-slate-500'} />
                                  <span className={isEnabled ? 'text-slate-200 font-medium' : 'text-slate-400'}>{tool.metadata.name}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  {isEnabled && (
                                    <button
                                      onClick={() => setSelectedToolConfigId(selectedToolConfigId === tool.metadata.id ? null : tool.metadata.id)}
                                      className={`p-1 rounded transition-colors hover:bg-slate-800 ${
                                        selectedToolConfigId === tool.metadata.id ? 'text-pink-400' : 'text-slate-400'
                                      }`}
                                    >
                                      <Icons.Settings size={11} />
                                    </button>
                                  )}
                                  <input
                                    type="checkbox"
                                    checked={isEnabled}
                                    onChange={toggleTool}
                                    className="rounded border-slate-700 bg-slate-900 text-pink-500 focus:ring-0 focus:ring-offset-0 w-3 h-3 cursor-pointer"
                                  />
                                </div>
                              </div>
                              
                              {isEnabled && selectedToolConfigId === tool.metadata.id && (
                                <div className="mt-1 border-t border-slate-800/80 pt-2 flex flex-col gap-2 bg-slate-950/40 p-2 rounded">
                                  <div className="flex flex-col gap-0.5">
                                    <label className="text-[8px] font-bold text-slate-500">CREDENTIAL ID</label>
                                    <select
                                      className="w-full bg-slate-900 border border-slate-700/60 rounded px-1.5 py-0.5 text-[9px] text-foreground focus:outline-none focus:ring-1 focus:ring-pink-500"
                                      value={String(toolConfig.credential_id || 'default-key')}
                                      onChange={(e) => {
                                        const updated = toolsList.map((t: any) =>
                                          t.id === tool.metadata.id ? { ...t, credential_id: e.target.value } : t
                                        );
                                        CommandBus.dispatch(new UpdateNodePropertyCommand(id, { tools: updated }));
                                      }}
                                    >
                                      <option value="default-key">Default Settings Key</option>
                                      {credentialsList.map((c) => (
                                        <option key={c.credential_id} value={c.credential_id}>{c.credential_id}</option>
                                      ))}
                                    </select>
                                  </div>
                                  
                                  {tool.metadata.id === 'google_sheets' && (
                                    <>
                                      <div className="flex flex-col gap-0.5">
                                        <label className="text-[8px] font-bold text-slate-500">SPREADSHEET ID</label>
                                        <input
                                          type="text"
                                          placeholder="default_sheet"
                                          className="w-full bg-slate-900 border border-slate-700/60 rounded px-1.5 py-0.5 text-[9px] text-foreground focus:outline-none focus:ring-1 focus:ring-pink-500"
                                          value={String(toolConfig.spreadsheet_id || '')}
                                          onChange={(e) => {
                                            const updated = toolsList.map((t: any) =>
                                              t.id === tool.metadata.id ? { ...t, spreadsheet_id: e.target.value } : t
                                            );
                                            CommandBus.dispatch(new UpdateNodePropertyCommand(id, { tools: updated }));
                                          }}
                                        />
                                      </div>
                                      <div className="flex flex-col gap-0.5">
                                        <label className="text-[8px] font-bold text-slate-500">SHEET NAME / RANGE</label>
                                        <input
                                          type="text"
                                          placeholder="Sheet1"
                                          className="w-full bg-slate-900 border border-slate-700/60 rounded px-1.5 py-0.5 text-[9px] text-foreground focus:outline-none font-sans"
                                          value={String(toolConfig.range || '')}
                                          onChange={(e) => {
                                            const updated = toolsList.map((t: any) =>
                                              t.id === tool.metadata.id ? { ...t, range: e.target.value } : t
                                            );
                                            CommandBus.dispatch(new UpdateNodePropertyCommand(id, { tools: updated }));
                                          }}
                                        />
                                      </div>
                                    </>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })()}
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
        {plugin.metadata.id === 'send-email' && (
          <div className="text-xs flex flex-col gap-0.5">
            <span className="text-rose-400 font-mono text-[10px]">{String(data.recipient || '')}</span>
            <p className="text-muted-foreground text-[10px] truncate">{String(data.subject || '')}</p>
          </div>
        )}
        {plugin.metadata.id === 'read-excel' && (
          <div className="text-xs flex flex-col gap-0.5">
            <span className="text-emerald-400 font-mono text-[10px]">Path: {String(data.file_path || '')}</span>
            <span className="text-muted-foreground text-[10px]">Output: {String(data.output_var || 'rows')}</span>
          </div>
        )}
        {plugin.metadata.id === 'loop' && (
          <div className="text-xs flex flex-col gap-0.5">
            <span className="text-amber-400 font-mono text-[10px]">Loop: {String(data.items_var || 'rows')}</span>
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

      {plugin.metadata.id === 'ai_agent' && (
        <div className="flex justify-between border-t border-slate-800 bg-[#0e1424]/60 px-6 py-2.5 text-[9px] font-mono text-slate-400 rounded-b-xl relative">
          <div className="flex flex-col items-center gap-0.5 relative">
            <span className="text-[8px] text-slate-400 font-semibold uppercase tracking-wider">Chat Model*</span>
            <Handle
              type="target"
              id="chat_model"
              position={Position.Bottom}
              style={{ background: '#3b82f6', border: '2px solid #1e3a8a', bottom: '-15px', width: 10, height: 10 }}
            />
          </div>
          <div className="flex flex-col items-center gap-0.5 relative">
            <span className="text-[8px] text-slate-400 font-semibold uppercase tracking-wider">Memory</span>
            <Handle
              type="target"
              id="memory"
              position={Position.Bottom}
              style={{ background: '#6366f1', border: '2px solid #312e81', bottom: '-15px', width: 10, height: 10 }}
            />
          </div>
          <div className="flex flex-col items-center gap-0.5 relative">
            <span className="text-[8px] text-slate-400 font-semibold uppercase tracking-wider">Tool</span>
            <Handle
              type="target"
              id="tool"
              position={Position.Bottom}
              style={{ background: '#ec4899', border: '2px solid #831843', bottom: '-15px', width: 10, height: 10 }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
export default CustomNode;

