import type { Workflow } from '../models/workflow';
import type { NodePlugin } from '../plugins/plugin';


export interface ValidationIssue {
  type: 'error' | 'warning';
  nodeId?: string;
  message: string;
}

export class BuildValidation {
  public static validate(workflow: Workflow, plugins: Map<string, NodePlugin>): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    // 1. Structural Checks (Disconnected nodes, cyclic loops)
    const hasTrigger = workflow.nodes.some(n => {
      const plugin = plugins.get(n.type);
      return plugin?.capabilities.trigger === true;
    });

    if (workflow.nodes.length > 0 && !hasTrigger) {
      issues.push({
        type: 'warning',
        message: 'The workflow has no trigger node. It can only be triggered manually.',
      });
    }

    // Check for cycles using DFS
    const adjList: Map<string, string[]> = new Map();
    workflow.nodes.forEach(n => adjList.set(n.id, []));
    workflow.edges.forEach(e => {
      if (adjList.has(e.source)) {
        adjList.get(e.source)!.push(e.target);
      }
    });

    const visited = new Set<string>();
    const recStack = new Set<string>();
    let hasCycle = false;

    function dfs(nodeId: string) {
      visited.add(nodeId);
      recStack.add(nodeId);

      const neighbors = adjList.get(nodeId) || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          dfs(neighbor);
        } else if (recStack.has(neighbor)) {
          hasCycle = true;
        }
      }
      recStack.delete(nodeId);
    }

    workflow.nodes.forEach(n => {
      if (!visited.has(n.id)) {
        dfs(n.id);
      }
    });

    if (hasCycle) {
      issues.push({
        type: 'error',
        message: 'Workflow contains a circular dependency loop. Cycles are not supported.',
      });
    }

    // 2. Schema check on each node configuration
    workflow.nodes.forEach(n => {
      const plugin = plugins.get(n.type);
      if (!plugin) {
        issues.push({
          type: 'error',
          nodeId: n.id,
          message: `Unknown node type: "${n.type}" (Missing Plugin).`,
        });
        return;
      }

      // Dynamic field schema validation
      const result = plugin.validate(n.data);
      if (!result.isValid) {
        result.errors.forEach(err => {
          issues.push({
            type: 'error',
            nodeId: n.id,
            message: `${plugin.metadata.name}: ${err}`,
          });
        });
      }
    });

    return issues;
  }
}

export class ExecutionValidation {
  public static validate(workflow: Workflow, plugins: Map<string, NodePlugin>): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    // 1. Assert credentials configurations
    workflow.nodes.forEach(n => {
      const plugin = plugins.get(n.type);
      if (plugin?.capabilities.credentialRequired) {
        if (!n.data.credentialId) {
          issues.push({
            type: 'error',
            nodeId: n.id,
            message: `${plugin.metadata.name} requires credentials, but none are selected.`,
          });
        }
      }
    });

    return issues;
  }
}
