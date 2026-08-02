// Value Objects
export type WorkflowId = string;
export type NodeId = string;
export type EdgeId = string;
export type PluginId = string;
export type Version = number;
export type ExecutionId = string;

export interface WorkflowMetadata {
  id: WorkflowId;
  name: string;
  description: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowNode {
  id: NodeId;
  type: string;
  version: Version;
  position: { x: number; y: number };
  data: Record<string, unknown>;
  label?: string;
}

export interface WorkflowEdge {
  id: EdgeId;
  source: NodeId;
  target: NodeId;
  sourceHandle?: string;
  targetHandle?: string;
  label?: string;
}

// Domain Event Contract
export interface DomainEvent {
  id: string;
  occurredAt: Date;
  name: string;
  payload: Record<string, unknown>;
}

// Workflow Aggregate Root
export class Workflow {
  public readonly formatVersion: number;
  public readonly engineVersion: number;
  public readonly nodeRegistryVersion: number;
  public readonly workflowVersion: Version;
  public readonly metadata: WorkflowMetadata;
  public readonly nodes: WorkflowNode[];
  public readonly edges: WorkflowEdge[];
  public readonly variables: Record<string, unknown>;

  constructor(
    formatVersion: number,
    engineVersion: number,
    nodeRegistryVersion: number,
    workflowVersion: Version,
    metadata: WorkflowMetadata,
    nodes: WorkflowNode[],
    edges: WorkflowEdge[],
    variables: Record<string, unknown> = {}
  ) {
    this.formatVersion = formatVersion;
    this.engineVersion = engineVersion;
    this.nodeRegistryVersion = nodeRegistryVersion;
    this.workflowVersion = workflowVersion;
    this.metadata = metadata;
    this.nodes = nodes;
    this.edges = edges;
    this.variables = variables;
  }


  public serialize(): string {
    return JSON.stringify({
      formatVersion: this.formatVersion,
      engineVersion: this.engineVersion,
      nodeRegistryVersion: this.nodeRegistryVersion,
      workflowVersion: this.workflowVersion,
      metadata: this.metadata,
      variables: this.variables,
      nodes: this.nodes,
      edges: this.edges,
    }, null, 2);
  }
}
