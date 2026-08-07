import React from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  SelectionMode,
} from '@xyflow/react';
import type {
  Connection,
  ReactFlowInstance,
  OnNodesChange,
  OnEdgesChange,
  Edge,
  Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import * as Icons from 'lucide-react';

import { useWorkflowProjection } from '../../application/services';
import {
  CommandBus,
  CreateNodeCommand,
  ConnectNodesCommand,
  MoveNodeCommand,
  DeleteNodeCommand,
  DuplicateNodeCommand,
  DeleteEdgeCommand,
} from '../../application/commands/commandBus';
import CustomNode from './CustomNode';
import { mapWorkflowToReactFlow } from '../mappers/workflowToReactFlow';
import type { WorkflowNode, WorkflowEdge } from '../../domain/models/workflow';
import { useToast } from '../../../../shared/components/Toast';

const nodeTypes = {
  custom: CustomNode,
};

export const FlowCanvas: React.FC = () => {
  const { nodes, edges, selectNode, historyVersion } = useWorkflowProjection();
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<any>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<any>([]);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<ReactFlowInstance | null>(null);

  // Canvas control toggles loaded from local UI preferences
  const [showGrid, setShowGrid] = React.useState(() => {
    return localStorage.getItem('fluxa_ui_show_grid') !== 'false';
  });
  const [showMiniMap, setShowMiniMap] = React.useState(() => {
    return localStorage.getItem('fluxa_ui_show_minimap') !== 'false';
  });
  const [snapToGrid, setSnapToGrid] = React.useState(() => {
    return localStorage.getItem('fluxa_ui_snap_to_grid') === 'true';
  });

  const toggleGrid = () => setShowGrid(prev => {
    const next = !prev;
    localStorage.setItem('fluxa_ui_show_grid', String(next));
    return next;
  });

  const toggleMiniMap = () => setShowMiniMap(prev => {
    const next = !prev;
    localStorage.setItem('fluxa_ui_show_minimap', String(next));
    return next;
  });

  const toggleSnap = () => setSnapToGrid(prev => {
    const next = !prev;
    localStorage.setItem('fluxa_ui_snap_to_grid', String(next));
    return next;
  });

  // Context Menus
  const [contextMenu, setContextMenu] = React.useState<{
    x: number;
    y: number;
    type: 'node' | 'canvas';
    nodeId?: string;
  } | null>(null);

  const copiedNodeRef = React.useRef<any>(null);
  const { showToast } = useToast();
  const dragStartPositions = React.useRef<Record<string, { x: number; y: number }>>({});

  // Sync presentation nodes/edges with Domain state projections
  React.useEffect(() => {
    const { rfNodes: mappedNodes, rfEdges: mappedEdges } = mapWorkflowToReactFlow(nodes, edges);
    setRfNodes(mappedNodes);
    setRfEdges(mappedEdges);
  }, [nodes, edges, historyVersion, setRfNodes, setRfEdges]);

  // Keyboard Shortcuts (Item 4)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input/textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)) return;

      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        if (e.shiftKey) {
          e.preventDefault();
          if (CommandBus.canRedo()) {
            CommandBus.redo();
            showToast('Redo executed', 'info', 1500);
          }
        } else {
          e.preventDefault();
          if (CommandBus.canUndo()) {
            CommandBus.undo();
            showToast('Undo executed', 'info', 1500);
          }
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        if (CommandBus.canRedo()) {
          CommandBus.redo();
          showToast('Redo executed', 'info', 1500);
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        const selectedRfNode = rfNodes.find((n) => n.selected);
        if (selectedRfNode) {
          CommandBus.dispatch(new DuplicateNodeCommand(selectedRfNode.id));
          showToast('Node duplicated', 'success', 2000);
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
        const selectedRfNode = rfNodes.find((n) => n.selected);
        if (selectedRfNode) {
          copiedNodeRef.current = selectedRfNode;
          showToast('Node copied to clipboard', 'info', 1500);
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
        e.preventDefault();
        if (copiedNodeRef.current) {
          CommandBus.dispatch(new DuplicateNodeCommand(copiedNodeRef.current.id));
          showToast('Node pasted', 'success', 2000);
        }
      } else if (e.key === 'Escape') {
        setContextMenu(null);
        selectNode(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [rfNodes, showToast, selectNode]);

  // Connect handler with default Edge Labels support (Item 10)
  const onConnect = React.useCallback(
    (params: Connection) => {
      // UI Level: Self-connection guard
      if (params.source === params.target) {
        showToast('Cannot connect a node to itself', 'warning');
        return;
      }

      // UI Level: Duplicate connection guard (matching source, target, and handles)
      const existingEdges = useWorkflowProjection.getState().edges;
      const isDuplicate = existingEdges.some(e =>
        e.source === params.source &&
        e.target === params.target &&
        e.sourceHandle === (params.sourceHandle || undefined) &&
        e.targetHandle === (params.targetHandle || undefined)
      );
      if (isDuplicate) {
        showToast('Connection already exists', 'warning');
        return;
      }

      const edge: WorkflowEdge = {
        id: `e-${params.source}-${params.target}-${Date.now().toString(36)}`,
        source: params.source,
        target: params.target,
        sourceHandle: params.sourceHandle || undefined,
        targetHandle: params.targetHandle || undefined,
        label: undefined,
      };

      try {
        CommandBus.dispatch(new ConnectNodesCommand(edge));
        showToast('Nodes connected', 'success', 2000);
      } catch (err: any) {
        showToast(err.message || 'Failed to connect nodes', 'error');
      }
    },
    [showToast]
  );

  // Drag over handler
  const onDragOver = React.useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Drop handler
  const onDrop = React.useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type =
        event.dataTransfer.getData('application/reactflow-type') ||
        event.dataTransfer.getData('application/reactflow');
      if (!type || !reactFlowInstance) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: WorkflowNode = {
        id: `${type}-${Math.random().toString(36).substr(2, 9)}`,
        type,
        version: 1,
        position,
        data: {},
      };

      CommandBus.dispatch(new CreateNodeCommand(newNode));
      showToast('Node added to canvas', 'success', 2000);
    },
    [reactFlowInstance, showToast]
  );

  // Handle node movement history
  const onNodeDragStart = React.useCallback((_event: any, node: Node) => {
    dragStartPositions.current[node.id] = { ...node.position };
  }, []);

  const onNodeDragStop = React.useCallback((_event: any, node: Node) => {
    const oldPos = dragStartPositions.current[node.id];
    CommandBus.dispatch(new MoveNodeCommand(node.id, node.position, oldPos));
    delete dragStartPositions.current[node.id];
  }, []);

  // Context Menu outside pointerdown dismissal
  React.useEffect(() => {
    if (!contextMenu) return;
    const handlePointerDown = (e: PointerEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest('.context-menu-container')) return;
      setContextMenu(null);
    };
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [contextMenu]);

  // Handle node selection
  const onNodeClick = React.useCallback(
    (_event: any, node: Node) => {
      selectNode(node.id);
      setContextMenu(null);
    },
    [selectNode]
  );

  // Handle pane click
  const onPaneClick = React.useCallback(() => {
    selectNode(null);
    setContextMenu(null);
  }, [selectNode]);

  // Context menu on Node right-click (Item 11)
  const onNodeContextMenu = React.useCallback(
    (event: any, node: Node) => {
      event.preventDefault();
      selectNode(node.id);
      setContextMenu({
        x: event.clientX,
        y: event.clientY,
        type: 'node',
        nodeId: node.id,
      });
    },
    [selectNode]
  );

  // Context menu on Canvas right-click (Item 11)
  const onPaneContextMenu = React.useCallback((event: any) => {
    event.preventDefault();
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      type: 'canvas',
    });
  }, []);

  // Deletion handlers
  const onNodesDelete = React.useCallback(
    (deleted: Node[]) => {
      deleted.forEach((node) => {
        CommandBus.dispatch(new DeleteNodeCommand(node.id));
      });
      showToast('Node deleted', 'info', 2000);
    },
    [showToast]
  );

  const onEdgesDelete = React.useCallback(
    (deleted: Edge[]) => {
      deleted.forEach((edge) => {
        CommandBus.dispatch(new DeleteEdgeCommand(edge.id));
      });
      showToast('Edge removed', 'info', 2000);
    },
    [showToast]
  );

  // Context menu action helpers
  const handleContextAction = (action: string) => {
    if (!contextMenu) return;
    if (contextMenu.type === 'node' && contextMenu.nodeId) {
      if (action === 'duplicate') {
        CommandBus.dispatch(new DuplicateNodeCommand(contextMenu.nodeId));
        showToast('Node duplicated', 'success');
      } else if (action === 'delete') {
        CommandBus.dispatch(new DeleteNodeCommand(contextMenu.nodeId));
        showToast('Node deleted', 'info');
      }
    } else if (contextMenu.type === 'canvas') {
      if (action === 'fit') {
        reactFlowInstance?.fitView({ duration: 300 });
      }
    }
    setContextMenu(null);
  };

  return (
    <div className="w-full h-full relative bg-slate-950/20" onDragOver={onDragOver} onDrop={onDrop}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange as OnNodesChange}
        onEdgesChange={onEdgesChange as OnEdgesChange}
        onNodesDelete={onNodesDelete}
        onEdgesDelete={onEdgesDelete}
        onConnect={onConnect}
        onNodeDragStart={onNodeDragStart}
        onNodeDragStop={onNodeDragStop}
        onNodeClick={onNodeClick}
        onNodeContextMenu={onNodeContextMenu}
        onPaneClick={onPaneClick}
        onPaneContextMenu={onPaneContextMenu}
        nodeTypes={nodeTypes}
        onInit={setReactFlowInstance}
        selectionMode={SelectionMode.Partial}
        selectionOnDrag={true}
        snapToGrid={snapToGrid}
        snapGrid={[16, 16]}
        defaultEdgeOptions={{
          type: 'default',
          animated: true,
          style: { stroke: 'hsl(var(--primary))', strokeWidth: 2.5 },
        }}
        fitView
      >
        {showGrid && <Background color="hsl(var(--border))" gap={16} size={1} />}
        <Controls className="bg-card border border-border text-card-foreground rounded-md shadow-md" />
        {showMiniMap && (
          <MiniMap
            style={{
              background: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
            nodeColor={(n) => (n.selected ? 'hsl(var(--primary))' : 'hsl(var(--muted-foreground))')}
          />
        )}
      </ReactFlow>

      {/* Floating Canvas Controls Bar (Item 2) */}
      <div className="absolute bottom-4 left-4 z-20 flex items-center gap-1 p-1.5 rounded-xl bg-card/90 border border-border shadow-xl backdrop-blur-md">
        <button
          onClick={toggleGrid}
          className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            showGrid ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
          title="Toggle Grid"
        >
          <Icons.Grid size={14} />
          <span className="hidden sm:inline">Grid</span>
        </button>
        <button
          onClick={toggleMiniMap}
          className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            showMiniMap ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
          title="Toggle MiniMap"
        >
          <Icons.Map size={14} />
          <span className="hidden sm:inline">Map</span>
        </button>
        <button
          onClick={toggleSnap}
          className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            snapToGrid ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
          title="Toggle Snap to Grid"
        >
          <Icons.Magnet size={14} />
          <span className="hidden sm:inline">Snap</span>
        </button>
        <div className="w-[1px] h-6 bg-border mx-1" />
        <button
          onClick={() => reactFlowInstance?.fitView({ duration: 300 })}
          className="p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          title="Fit View"
        >
          <Icons.Maximize2 size={15} />
          <span className="hidden sm:inline">Fit</span>
        </button>
      </div>

      {/* Right-Click Context Menu (Item 11) */}
      {contextMenu && (() => {
        // Boundary-aware positioning
        const menuWidth = 160;
        const menuHeight = contextMenu.type === 'node' ? 82 : 42;
        const adjustedX = Math.min(contextMenu.x, window.innerWidth - menuWidth - 8);
        const adjustedY = Math.min(contextMenu.y, window.innerHeight - menuHeight - 8);

        return (
          <div
            className="fixed z-50 bg-card border border-border rounded-xl shadow-2xl py-1.5 min-w-[160px] text-xs font-semibold animate-in fade-in zoom-in-95 duration-100 context-menu-container"
            style={{ top: adjustedY, left: adjustedX }}
          >
            {contextMenu.type === 'node' ? (
              <>
                <button
                  onClick={() => handleContextAction('duplicate')}
                  className="w-full px-3 py-2 text-left flex items-center gap-2 hover:bg-secondary transition-colors text-foreground"
                >
                  <Icons.Copy size={13} />
                  <span>Duplicate Node</span>
                </button>
                <button
                  onClick={() => handleContextAction('delete')}
                  className="w-full px-3 py-2 text-left flex items-center gap-2 hover:bg-destructive hover:text-white transition-colors text-destructive"
                >
                  <Icons.Trash2 size={13} />
                  <span>Delete Node</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => handleContextAction('fit')}
                  className="w-full px-3 py-2 text-left flex items-center gap-2 hover:bg-secondary transition-colors text-foreground"
                >
                  <Icons.Maximize2 size={13} />
                  <span>Fit Canvas View</span>
                </button>
              </>
            )}
          </div>
        );
      })()}
    </div>
  );
};
export default FlowCanvas;
