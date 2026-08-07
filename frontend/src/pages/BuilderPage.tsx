import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as Icons from 'lucide-react';
import FlowCanvas from '../features/builder/presentation/components/FlowCanvas';
import NodePalette from '../features/builder/presentation/components/NodePalette';
import PropertyPanel from '../features/builder/presentation/components/PropertyPanel';
import { CommandPalette } from '../features/builder/presentation/components/CommandPalette';
import { CommandBus } from '../features/builder/application/commands/commandBus';
import { useWorkflowProjection, BuildValidation, nodeRegistry, useUIProjection, eventBus } from '../features/builder/application/services';
import { Workflow } from '../features/builder/domain/models/workflow';
import { useToast } from '../shared/components/Toast';
import { PackageBrowserModal } from '../features/builder/presentation/components/PackageBrowserModal';
import { AppError } from '../shared/errors/AppError';


export const BuilderPage: React.FC = () => {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();
  const { nodes, edges, variables, metadata, isDirty, setDirty, setWorkflow } = useWorkflowProjection();
  const { activePanel, setActivePanel } = useUIProjection();
  const [validationIssues, setValidationIssues] = React.useState<any[]>([]);
  const { showToast } = useToast();
  const [isPackageBrowserOpen, setIsPackageBrowserOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [notFound, setNotFound] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [loadError, setLoadError] = React.useState<string | null>(null);


  // 1. Fetch initial workflow structure from DB on mount / switch
  React.useEffect(() => {
    if (!workflowId) return;

    // Immediately isolate and clear previous workflow states
    setLoading(true);
    setNotFound(false);
    setLoadError(null);
    CommandBus.clearHistory();
    useWorkflowProjection.getState().clearState();

    import('../features/builder/infrastructure/api/workflowRepository').then(({ workflowRepositoryInstance }) => {
      workflowRepositoryInstance.getById(workflowId)
        .then((wf) => {
          setWorkflow({
            metadata: wf.metadata,
            nodes: wf.nodes,
            edges: wf.edges,
            variables: wf.variables
          });
          setDirty(false);
          setLoading(false);
        })
        .catch((err) => {
          console.error("Failed to load workflow:", err);
          if (err instanceof AppError && err.isNotFound()) {
            setNotFound(true);
          } else {
            setLoadError(err.message || 'Error loading workflow.');
          }
          setLoading(false);
        });
    });
  }, [workflowId, setWorkflow, setDirty]);

  // Build Validation dynamic updates
  React.useEffect(() => {
    nodeRegistry.getPlugins().then((plugins) => {
      const w = new Workflow(1, 1, 1, 1, metadata, nodes, edges, variables);
      const issues = BuildValidation.validate(w, plugins);
      setValidationIssues(issues);
    });
  }, [nodes, edges, variables, metadata]);

  // Save changes handler
  const handleSave = async () => {
    if (loading || saving || !workflowId) return;
    setSaving(true);
    try {
      const { workflowRepositoryInstance } = await import('../features/builder/infrastructure/api/workflowRepository');
      // Ensure the model metadata has the correct resolved ID
      const w = new Workflow(1, 1, 1, 1, { ...metadata, id: workflowId }, nodes, edges, variables);
      
      // Save directly to backend API database
      await workflowRepositoryInstance.save(w);
      showToast('Workflow saved successfully on backend!', 'success');
      setDirty(false);
    } catch (err: any) {
      console.error(err);
      const msg = err.message || 'Failed to save workflow';
      showToast(msg, 'error');
      // DO NOT clear dirty flag on save failure! Keep user edits intact.
    } finally {
      setSaving(false);
    }
  };


  // Run execution handler
  const handleRun = async () => {
    if (loading || !workflowId) return;
    const hasErrors = validationIssues.some(iss => iss.type === 'error');
    if (hasErrors) {
      showToast('Cannot execute: Workflow contains structural validation errors!', 'error');
      return;
    }
    
    try {
      // 1. Save current workflow changes first via api updates
      const response = await fetch(`/api/v1/workflows/${workflowId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trigger_type: 'manual',
          variables: variables || {}
        })
      });
      
      if (!response.ok) {
        throw new Error('API execution failed');
      }
      
      const execResult = await response.json();
      const execId = execResult.id;
      
      eventBus.listenToExecution(execId);
      showToast(`Triggered Real Backend Execution ID: ${execId}. Go to Executions tab to see live logs.`, 'success');
    } catch (err: any) {
      console.error(err);
      // Fallback to local simulation if Backend API/Temporal is offline
      const execId = `exec-${Math.random().toString(36).substr(2, 9)}`;
      eventBus.listenToExecution(execId);
      showToast(`Triggered Simulation Run: ${execId} (Backend connection error)`, 'warning');
    }
  };

  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/reactflow-type', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  if (notFound) {
    return (
      <div className="flex-1 h-full flex flex-col items-center justify-center text-center p-6 bg-background">
        <div className="text-6xl font-black text-primary mb-4 font-mono">404</div>
        <h2 className="text-xl font-bold text-foreground mb-2">Workflow Not Found</h2>
        <p className="text-sm text-muted-foreground mb-6">
          The workflow you are looking for does not exist or has been deleted.
        </p>
        <button
          onClick={() => navigate('/workflows')}
          className="px-4 py-2 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
        >
          Return to Workflows
        </button>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex-1 h-full flex flex-col items-center justify-center text-center p-6 bg-background">
        <div className="text-5xl font-black text-amber-500 mb-4 font-mono">Backend Offline</div>
        <h2 className="text-xl font-bold text-foreground mb-2">Service Connection Error</h2>
        <p className="text-sm text-muted-foreground mb-6 max-w-md">
          {loadError}
        </p>
        <button
          onClick={() => navigate('/workflows')}
          className="px-4 py-2 bg-secondary hover:bg-secondary/80 text-foreground text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
        >
          Return to Workflows
        </button>
      </div>
    );
  }


  return (
    <div className="flex-1 h-full flex flex-col overflow-hidden bg-background">
      {/* Top action bar */}
      <header className="h-14 border-b border-border glass flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-3">
          <Icons.CodeXml className="text-primary" size={18} />
          <h1 className="font-bold text-sm text-foreground m-0">{loading ? 'Loading...' : metadata.name}</h1>
          {isDirty && !loading && (
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
            disabled={loading || !CommandBus.canUndo()}
            className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
            title="Undo"
          >
            <Icons.Undo size={14} />
          </button>
          <button
            onClick={() => CommandBus.redo()}
            disabled={loading || !CommandBus.canRedo()}
            className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
            title="Redo"
          >
            <Icons.Redo size={14} />
          </button>

          <div className="w-[1px] h-4 bg-border/50 mx-2" />

          {/* Validation badge */}
          {validationIssues.length > 0 && !loading ? (
            <div className="flex items-center gap-1.5 px-3 py-1 bg-red-500/10 border border-red-500/20 text-red-500 rounded-md text-xs font-semibold">
              <Icons.AlertTriangle size={12} />
              {validationIssues.filter(i => i.type === 'error').length} Errors
            </div>
          ) : !loading ? (
            <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-md text-xs font-semibold">
              <Icons.CheckCircle size={12} />
              Valid
            </div>
          ) : null}

          <div className="w-[1px] h-4 bg-border/50 mx-2" />

          {/* Save/Run */}
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-1.5 rounded-xl border skeuo-btn text-foreground text-xs cursor-pointer disabled:opacity-40"
          >
            <Icons.Save size={13} />
            Save
          </button>
          <button
            onClick={handleRun}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-1.5 rounded-xl border skeuo-btn-primary text-white text-xs cursor-pointer disabled:opacity-40"
          >
            <Icons.Play size={13} fill="white" />
            Run
          </button>


          {/* Configuration sidebar toggle */}
          <button
            onClick={() => setActivePanel(activePanel === 'properties' ? 'palette' : 'properties')}
            disabled={loading}
            className={`p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40 ${
              activePanel === 'properties' ? 'bg-primary/20 text-primary' : ''
            }`}
          >
            <Icons.SlidersHorizontal size={14} />
          </button>
        </div>
      </header>

      {/* Main split work area */}
      <div className="flex-1 flex overflow-hidden">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
            <Icons.Loader className="animate-spin text-primary mr-2" size={16} />
            Loading canvas editor...
          </div>
        ) : (
          <>
            {/* Left Side: Palette */}
            {activePanel === 'palette' && (
              <aside className="w-[280px] h-full">
                <NodePalette
                  onDragStart={onDragStart}
                  onOpenPackageBrowser={() => setIsPackageBrowserOpen(true)}
                />
              </aside>
            )}

            {/* Center: Interactive React Flow Canvas */}
            <main className="flex-1 h-full relative">
              <FlowCanvas />
              {/* Floating shortcut help banner */}
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-4 border border-black/40 rounded-xl px-3 py-1.5 text-[10px] text-muted-foreground z-10 skeuo-raised">
                <span className="flex items-center gap-1"><kbd className="bg-muted px-1.5 py-0.5 rounded font-mono">Delete</kbd> Delete node</span>
                <span className="flex items-center gap-1"><kbd className="bg-muted px-1.5 py-0.5 rounded font-mono">Ctrl+K / Alt+K</kbd> Command palette</span>
              </div>
            </main>

            {/* Right Side: Properties configuration Panel */}
            {activePanel === 'properties' && (
              <aside className="w-[320px] h-full">
                <PropertyPanel />
              </aside>
            )}
          </>
        )}
      </div>

      {/* Ctrl+K Command Overlay */}
      <CommandPalette onRunWorkflow={handleRun} />

      {/* Package Browser Modal */}
      <PackageBrowserModal isOpen={isPackageBrowserOpen} onClose={() => setIsPackageBrowserOpen(false)} />
    </div>
  );
};
export default BuilderPage;
