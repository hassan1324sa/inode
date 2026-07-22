import React from 'react';
import * as Icons from 'lucide-react';
import FlowCanvas from '../features/builder/presentation/components/FlowCanvas';
import NodePalette from '../features/builder/presentation/components/NodePalette';
import PropertyPanel from '../features/builder/presentation/components/PropertyPanel';
import CommandPalette from '../features/builder/presentation/components/CommandPalette';
import { CommandBus } from '../features/builder/application/commands/commandBus';
import { useWorkflowProjection, BuildValidation, nodeRegistry, useUIProjection, eventBus } from '../features/builder/application/services';
import { Workflow } from '../features/builder/domain/models/workflow';


export const BuilderPage: React.FC = () => {
  const { nodes, edges, variables, metadata, isDirty, setDirty } = useWorkflowProjection();
  const { activePanel, setActivePanel } = useUIProjection();
  const [validationIssues, setValidationIssues] = React.useState<any[]>([]);

  // Build Validation dynamic updates
  React.useEffect(() => {
    nodeRegistry.getPlugins().then((plugins) => {
      const w = new Workflow(1, 1, 1, 1, metadata, nodes, edges, variables);
      const issues = BuildValidation.validate(w, plugins);
      setValidationIssues(issues);
    });
  }, [nodes, edges, variables, metadata]);

  // Save changes handler
  const handleSave = () => {
    alert('Workflow saved successfully!');
    setDirty(false);
  };

  // Run execution handler
  const handleRun = () => {
    const hasErrors = validationIssues.some(iss => iss.type === 'error');
    if (hasErrors) {
      alert('Cannot execute: Workflow contains structural validation errors!');
      return;
    }
    const execId = `exec-${Math.random().toString(36).substr(2, 9)}`;
    eventBus.listenToExecution(execId);
    alert(`Triggered Execution ID: ${execId}. Go to Executions tab to see live logs.`);
  };

  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="flex-1 h-full flex flex-col overflow-hidden bg-background">
      {/* Top action bar */}
      <header className="h-14 border-b border-border glass flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-3">
          <Icons.CodeXml className="text-primary" size={18} />
          <h1 className="font-bold text-sm text-foreground m-0">{metadata.name}</h1>
          {isDirty && (
            <span className="text-[10px] bg-amber-500/20 text-amber-500 border border-amber-500/30 px-2 py-0.5 rounded font-semibold">
              UNSAVED CHANGES
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Undo/Redo */}
          <button
            onClick={() => CommandBus.undo()}
            className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
            title="Undo"
          >
            <Icons.Undo size={14} />
          </button>
          <button
            onClick={() => CommandBus.redo()}
            className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
            title="Redo"
          >
            <Icons.Redo size={14} />
          </button>

          <div className="w-[1px] h-4 bg-border/50 mx-2" />

          {/* Validation badge */}
          {validationIssues.length > 0 ? (
            <div className="flex items-center gap-1.5 px-3 py-1 bg-red-500/10 border border-red-500/20 text-red-500 rounded-md text-xs font-semibold">
              <Icons.AlertTriangle size={12} />
              {validationIssues.filter(i => i.type === 'error').length} Errors
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-md text-xs font-semibold">
              <Icons.CheckCircle size={12} />
              Valid
            </div>
          )}

          <div className="w-[1px] h-4 bg-border/50 mx-2" />

          {/* Save/Run */}
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-3 py-1.5 bg-secondary hover:bg-secondary/80 border border-border text-foreground text-xs font-semibold rounded-md transition-colors"
          >
            <Icons.Save size={13} />
            Save
          </button>
          <button
            onClick={handleRun}
            className="flex items-center gap-2 px-4 py-1.5 bg-primary hover:bg-primary/90 text-white text-xs font-bold rounded-md shadow-md shadow-primary/20 transition-all active:scale-98"
          >
            <Icons.Play size={13} fill="white" />
            Run
          </button>

          {/* Configuration sidebar toggle */}
          <button
            onClick={() => setActivePanel(activePanel === 'properties' ? 'palette' : 'properties')}
            className={`p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors ${
              activePanel === 'properties' ? 'bg-primary/20 text-primary' : ''
            }`}
          >
            <Icons.SlidersHorizontal size={14} />
          </button>
        </div>
      </header>

      {/* Main split work area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Side: Palette */}
        {activePanel === 'palette' && (
          <aside className="w-[280px] h-full">
            <NodePalette onDragStart={onDragStart} />
          </aside>
        )}

        {/* Center: Interactive React Flow Canvas */}
        <main className="flex-1 h-full relative">
          <FlowCanvas />
        </main>

        {/* Right Side: Properties configuration Panel */}
        {activePanel === 'properties' && (
          <aside className="w-[320px] h-full">
            <PropertyPanel />
          </aside>
        )}
      </div>

      {/* Floating shortcut help banner */}
      <div className="absolute bottom-4 left-[300px] flex items-center gap-4 bg-slate-900/90 border border-border rounded-md px-3 py-1.5 text-[10px] text-muted-foreground z-10 glass">
        <span className="flex items-center gap-1"><kbd className="bg-muted px-1.5 py-0.5 rounded font-mono">Delete</kbd> Delete node</span>
        <span className="flex items-center gap-1"><kbd className="bg-muted px-1.5 py-0.5 rounded font-mono">Ctrl + K</kbd> Command palette</span>
      </div>

      {/* Ctrl+K Command Overlay */}
      <CommandPalette />
    </div>
  );
};
export default BuilderPage;
