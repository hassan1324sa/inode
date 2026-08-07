import { create } from 'zustand';
import type { WorkflowNode, WorkflowEdge, WorkflowMetadata } from '../../domain/models/workflow';
import { getCleanInitialWorkflowState } from '../../domain/seed/workflowSeeds';

interface WorkflowState {
  metadata: WorkflowMetadata;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables: Record<string, unknown>;
  selectedNodeId: string | null;
  isDirty: boolean;
  historyVersion: number; // Trigger re-renders on Undo/Redo

  setWorkflow: (workflow: { metadata: WorkflowMetadata; nodes: WorkflowNode[]; edges: WorkflowEdge[]; variables: Record<string, unknown> }) => void;
  updateNodes: (nodes: WorkflowNode[]) => void;
  updateEdges: (edges: WorkflowEdge[]) => void;
  selectNode: (nodeId: string | null) => void;
  updateNodeData: (nodeId: string, data: Record<string, unknown>) => void;
  setDirty: (isDirty: boolean) => void;
  incrementHistoryVersion: () => void;
  clearState: () => void;
}

const initialEmptyState = getCleanInitialWorkflowState('');

export const useWorkflowProjection = create<WorkflowState>((set) => ({
  metadata: initialEmptyState.metadata,
  nodes: initialEmptyState.nodes,
  edges: initialEmptyState.edges,
  variables: initialEmptyState.variables,
  selectedNodeId: null,
  isDirty: false,
  historyVersion: 0,

  setWorkflow: (workflow) => set({
    metadata: workflow.metadata,
    nodes: workflow.nodes,
    edges: workflow.edges,
    variables: workflow.variables,
    isDirty: false,
    selectedNodeId: null,
  }),
  updateNodes: (nodes) => set({ nodes, isDirty: true }),
  updateEdges: (edges) => set({ edges, isDirty: true }),
  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),
  updateNodeData: (nodeId, data) => set((state) => ({
    nodes: state.nodes.map((node) =>
      node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node
    ),
    isDirty: true,
  })),
  setDirty: (isDirty) => set({ isDirty }),
  incrementHistoryVersion: () => set((state) => ({ historyVersion: state.historyVersion + 1 })),
  clearState: () => set({
    metadata: getCleanInitialWorkflowState('').metadata,
    nodes: [],
    edges: [],
    variables: {},
    selectedNodeId: null,
    isDirty: false,
  }),
}));

