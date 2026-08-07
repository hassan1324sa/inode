import { useState } from "react";

export interface ExecutionDiffResult {
  workflow_structure_diff: {
    added_nodes: string[];
    removed_nodes: string[];
  };
  node_execution_diff: Record<string, { before: string; after: string }>;
  state_variable_diff: Record<string, { before: any; after: any }>;
}

export function useExecutionDiff(tenantId: string) {
  const [diff, setDiff] = useState<ExecutionDiffResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDiff = async (execIdA: string, execIdB: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/debug/executions/diff?execution_id_a=${execIdA}&execution_id_b=${execIdB}&tenant_id=${tenantId}`, {
        method: "POST"
      });
      if (!res.ok) throw new Error("Failed to fetch execution diff");
      const data = await res.json();
      setDiff(data);
      return data;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { diff, fetchDiff, loading, error };
}
