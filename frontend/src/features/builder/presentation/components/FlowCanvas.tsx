import React from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import type {
  Connection,
  ReactFlowInstance,
  OnNodesChange,
  OnEdgesChange,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useWorkflowProjection } from '../../application/services';
import { CommandBus, CreateNodeCommand, ConnectNodesCommand, MoveNodeCommand, DeleteNodeCommand } from '../../application/commands/commandBus';
import CustomNode from './CustomNode';
import { mapWorkflowToReactFlow } from '../mappers/workflowToReactFlow';
import type { WorkflowNode, WorkflowEdge } from '../../domain/models/workflow';

const nodeTypes = {
  custom: CustomNode,
};

export const FlowCanvas: React.FC = () => {
  const { nodes, edges, selectNode, historyVersion } = useWorkflowProjection();
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<any>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<any>([]);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<ReactFlowInstance | null>(null);


  // Sync presentation nodes/edges with Domain state projections (re-trigger on Command Bus changes)
  React.useEffect(() => {
    const { rfNodes: mappedNodes, rfEdges: mappedEdges } = mapWorkflowToReactFlow(nodes, edges);
    setRfNodes(mappedNodes);
    setRfEdges(mappedEdges);
  }, [nodes, edges, historyVersion, setRfNodes, setRfEdges]);

  // Connect handler
  const onConnect = React.useCallback(
    (params: Connection) => {
      const edge: WorkflowEdge = {
        id: `e-${params.source}-${params.target}`,
        source: params.source,
        target: params.target,
        sourceHandle: params.sourceHandle || undefined,
        targetHandle: params.targetHandle || undefined,
      };
      CommandBus.dispatch(new ConnectNodesCommand(edge));
    },
    []
  );

  // Node Drag end handler
  const onNodeDragStop = React.useCallback(
    (_event: any, node: any) => {
      CommandBus.dispatch(new MoveNodeCommand(node.id, node.position));
    },
    []
  );

  // Node Click Selection handler
  const onNodeClick = React.useCallback(
    (_event: any, node: any) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  // Pane click resets selection
  const onPaneClick = React.useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // Keyboard Delete node handler
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        const activeId = useWorkflowProjection.getState().selectedNodeId;
        // Don't trigger if typing in fields
        if (activeId && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
          CommandBus.dispatch(new DeleteNodeCommand(activeId));
          selectNode(null);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectNode]);

  // Drop handler for Node Palette drag items
  const onDragOver = React.useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = React.useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      if (!reactFlowInstance) return;

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

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
    },
    [reactFlowInstance]
  );

  return (
    <div className="w-full h-full relative bg-slate-950/20" onDragOver={onDragOver} onDrop={onDrop}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange as OnNodesChange}
        onEdgesChange={onEdgesChange as OnEdgesChange}
        onConnect={onConnect}
        onNodeDragStop={onNodeDragStop}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        onInit={setReactFlowInstance}
        fitView
      >
        <Background color="hsl(var(--border))" gap={16} size={1} />
        <Controls className="bg-slate-900 border border-border text-white rounded-md" />
        <MiniMap
          style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
          nodeColor={(n) => (n.selected ? 'hsl(var(--primary))' : 'rgba(255,255,255,0.1)')}
        />
      </ReactFlow>
    </div>
  );
};
export default FlowCanvas;
