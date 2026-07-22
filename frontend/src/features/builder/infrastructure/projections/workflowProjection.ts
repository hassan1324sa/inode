import { create } from 'zustand';
import type { WorkflowNode, WorkflowEdge, WorkflowMetadata } from '../../domain/models/workflow';


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
}

export const useWorkflowProjection = create<WorkflowState>((set) => ({
  metadata: {
    id: 'wf_lead_enrichment',
    name: 'AI Lead Enrichment & Response Draft',
    description: 'Enrich lead details via API and draft email using Gemini LLM',
    tags: ['AI', 'Sales', 'Enrichment'],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  nodes: [
    {
      id: 'node-set-variable',
      type: 'set_variable',
      version: 1,
      position: { x: 80, y: 150 },
      data: { variable_name: 'customer_email', variable_value: 'lead@corporate.com' },
    },
    {
      id: 'node-http-request',
      type: 'http_request',
      version: 1,
      position: { x: 380, y: 150 },
      data: { method: 'POST', url: 'https://api.company.com/enrich-lead', headers: '{}', body: '{"email": "{{customer_email}}"}' },
    },
    {
      id: 'node-ai-agent',
      type: 'ai_agent',
      version: 1,
      position: { x: 680, y: 150 },
      data: { model: 'gemini-1.5-flash', prompt: 'Draft a personalized upgrade proposal email for {{customer_email}} based on enriched CRM profile data.', credentialId: 'gemini-auth-key-1' },
    },
  ],
  edges: [
    {
      id: 'e-set-to-http',
      source: 'node-set-variable',
      target: 'node-http-request',
    },
    {
      id: 'e-http-to-ai',
      source: 'node-http-request',
      target: 'node-ai-agent',
    },
  ],
  variables: {},
  selectedNodeId: null,
  isDirty: false,
  historyVersion: 0,


  setWorkflow: (workflow) => set({
    metadata: workflow.metadata,
    nodes: workflow.nodes,
    edges: workflow.edges,
    variables: workflow.variables,
    isDirty: false,
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
}));
