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
