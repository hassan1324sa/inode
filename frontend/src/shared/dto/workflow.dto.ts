export interface WorkflowDTO {
  formatVersion: number;
  engineVersion: number;
  nodeRegistryVersion: number;
  workflowVersion: number;
  metadata: {
    id: string;
    name: string;
    description: string;
    tags: string[];
    createdAt: string;
    updatedAt: string;
  };
  variables: Record<string, unknown>;
  nodes: {
    id: string;
    type: string;
    version: number;
    position: { x: number; y: number };
    data: Record<string, unknown>;
  }[];
  edges: {
    id: string;
    source: string;
    target: string;
    sourceHandle?: string;
    targetHandle?: string;
    label?: string;
  }[];
}

export interface ExecutionEventDTO {
  id: string;
  executionId: string;
  type: string;
  nodeId?: string;
  timestamp: string;
  duration?: number;
  output?: Record<string, unknown>;
  error?: string;
}

export interface ExecutionSnapshotDTO {
  id: string;
  workflowId: string;
  status: string;
  currentNodeId?: string;
  completedNodes: string[];
  pendingNodes: string[];
  variables: Record<string, unknown>;
  logs: string[];
  startedAt: string;
  finishedAt?: string;
  duration: number;
  progressPercentage: number;
  estimatedRemainingSeconds?: number;
}
