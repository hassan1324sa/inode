import type { Command } from '../services/history';
import { HistoryManager } from '../services/history';
import type { WorkflowNode, WorkflowEdge, NodeId } from '../../domain/models/workflow';
import { useWorkflowProjection } from '../../infrastructure/projections/workflowProjection';

const history = new HistoryManager();

export class CreateNodeCommand implements Command {
  private node: WorkflowNode;

  constructor(node: WorkflowNode) {
    this.node = node;
  }

  public execute(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateNodes([...projection.nodes, this.node]);
  }

  public undo(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateNodes(projection.nodes.filter(n => n.id !== this.node.id));
  }
}

export class ConnectNodesCommand implements Command {
  private edge: WorkflowEdge;

  constructor(edge: WorkflowEdge) {
    this.edge = edge;
  }

  public execute(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateEdges([...projection.edges, this.edge]);
  }

  public undo(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateEdges(projection.edges.filter(e => e.id !== this.edge.id));
  }
}

export class DeleteNodeCommand implements Command {
  private deletedNode!: WorkflowNode;
  private deletedEdges!: WorkflowEdge[];
  private nodeId: NodeId;

  constructor(nodeId: NodeId) {
    this.nodeId = nodeId;
  }

  public execute(): void {
    const projection = useWorkflowProjection.getState();
    const node = projection.nodes.find(n => n.id === this.nodeId);
    if (node) {
      this.deletedNode = node;
      this.deletedEdges = projection.edges.filter(e => e.source === this.nodeId || e.target === this.nodeId);
      
      projection.updateNodes(projection.nodes.filter(n => n.id !== this.nodeId));
      projection.updateEdges(projection.edges.filter(e => e.source !== this.nodeId && e.target !== this.nodeId));
    }
  }

  public undo(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateNodes([...projection.nodes, this.deletedNode]);
    projection.updateEdges([...projection.edges, ...this.deletedEdges]);
  }
}

export class MoveNodeCommand implements Command {
  private oldPosition: { x: number; y: number };
  private nodeId: NodeId;
  private newPosition: { x: number; y: number };

  constructor(nodeId: NodeId, newPosition: { x: number; y: number }) {
    this.nodeId = nodeId;
    this.newPosition = newPosition;
    const node = useWorkflowProjection.getState().nodes.find(n => n.id === nodeId);
    this.oldPosition = node ? { ...node.position } : { x: 0, y: 0 };
  }

  public execute(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateNodes(projection.nodes.map(n => 
      n.id === this.nodeId ? { ...n, position: this.newPosition } : n
    ));
  }

  public undo(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateNodes(projection.nodes.map(n => 
      n.id === this.nodeId ? { ...n, position: this.oldPosition } : n
    ));
  }
}

export class UpdateNodePropertyCommand implements Command {
  private nodeId: NodeId;
  private oldData: any;
  private newData: any;

  constructor(nodeId: NodeId, newData: any) {
    this.nodeId = nodeId;
    this.newData = newData;
    const node = useWorkflowProjection.getState().nodes.find(n => n.id === nodeId);
    this.oldData = node ? { ...node.data } : {};
  }

  public execute(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateNodes(projection.nodes.map(n =>
      n.id === this.nodeId ? { ...n, data: this.newData } : n
    ));
  }

  public undo(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateNodes(projection.nodes.map(n =>
      n.id === this.nodeId ? { ...n, data: this.oldData } : n
    ));
  }
}

export class DeleteEdgeCommand implements Command {
  private deletedEdge: WorkflowEdge;

  constructor(edgeId: string) {
    const edge = useWorkflowProjection.getState().edges.find(e => e.id === edgeId);
    this.deletedEdge = edge || { id: edgeId, source: '', target: '' };
  }

  public execute(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateEdges(projection.edges.filter(e => e.id !== this.deletedEdge.id));
  }

  public undo(): void {
    const projection = useWorkflowProjection.getState();
    if (this.deletedEdge.source && this.deletedEdge.target) {
      projection.updateEdges([...projection.edges, this.deletedEdge]);
    }
  }
}

export class DuplicateNodeCommand implements Command {
  private originalNodeId: NodeId;
  private newNode!: WorkflowNode;

  constructor(nodeId: NodeId) {
    this.originalNodeId = nodeId;
  }

  public execute(): void {
    const projection = useWorkflowProjection.getState();
    const original = projection.nodes.find(n => n.id === this.originalNodeId);
    if (original) {
      const newId = `node-${Date.now()}`;
      const originalLabel = original.data?.label || original.label || 'Node';
      this.newNode = {
        ...original,
        id: newId,
        label: `${originalLabel} (Copy)`,
        data: {
          ...original.data,
          label: `${originalLabel} (Copy)`,
        },
        position: { x: original.position.x + 30, y: original.position.y + 30 }
      };
      projection.updateNodes([...projection.nodes, this.newNode]);
    }
  }

  public undo(): void {
    if (this.newNode) {
      const projection = useWorkflowProjection.getState();
      projection.updateNodes(projection.nodes.filter(n => n.id !== this.newNode.id));
    }
  }
}

export class DeleteSelectionCommand implements Command {
  private deletedNodes: WorkflowNode[] = [];
  private deletedEdges: WorkflowEdge[] = [];
  private nodeIds: string[];
  private edgeIds: string[];

  constructor(nodeIds: string[], edgeIds: string[]) {
    this.nodeIds = nodeIds;
    this.edgeIds = edgeIds;
  }

  public execute(): void {
    const projection = useWorkflowProjection.getState();
    this.deletedNodes = projection.nodes.filter(n => this.nodeIds.includes(n.id));
    this.deletedEdges = projection.edges.filter(
      e => this.edgeIds.includes(e.id) || this.nodeIds.includes(e.source) || this.nodeIds.includes(e.target)
    );

    const remainingNodes = projection.nodes.filter(n => !this.nodeIds.includes(n.id));
    const remainingEdges = projection.edges.filter(
      e => !this.edgeIds.includes(e.id) && !this.nodeIds.includes(e.source) && !this.nodeIds.includes(e.target)
    );

    projection.updateNodes(remainingNodes);
    projection.updateEdges(remainingEdges);
  }

  public undo(): void {
    const projection = useWorkflowProjection.getState();
    projection.updateNodes([...projection.nodes, ...this.deletedNodes]);
    projection.updateEdges([...projection.edges, ...this.deletedEdges]);
  }
}

export class CommandBus {
  public static dispatch(command: Command): void {
    history.execute(command);
    useWorkflowProjection.getState().incrementHistoryVersion();
  }

  public static undo(): void {
    history.undo();
    useWorkflowProjection.getState().incrementHistoryVersion();
  }

  public static redo(): void {
    history.redo();
    useWorkflowProjection.getState().incrementHistoryVersion();
  }

  public static canUndo(): boolean {
    return history.canUndo();
  }

  public static canRedo(): boolean {
    return history.canRedo();
  }
}

