import type { WorkflowNode, WorkflowEdge } from '../../domain/models/workflow';
import type { Node as RFNode, Edge as RFEdge } from '@xyflow/react';


export function mapNodeToReactFlow(node: WorkflowNode): RFNode {
  return {
    id: node.id,
    type: 'custom', // Single custom node handler dynamically driven by Schema
    position: node.position,
    data: {
      type: node.type,
      version: node.version,
      ...node.data,
    },
  };
}

export function mapEdgeToReactFlow(edge: WorkflowEdge): RFEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle,
    targetHandle: edge.targetHandle,
    type: 'smoothstep',
    animated: true,
  };
}

export function mapWorkflowToReactFlow(nodes: WorkflowNode[], edges: WorkflowEdge[]) {
  return {
    rfNodes: nodes.map(mapNodeToReactFlow),
    rfEdges: edges.map(mapEdgeToReactFlow),
  };
}
