import { useState } from "react";

export function useReplay(tenantId: string) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const triggerReplay = async (executionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/debug/executions/${executionId}/replay?tenant_id=${tenantId}`, {
        method: "POST"
      });
      if (!res.ok) throw new Error("Failed to trigger execution replay");
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const triggerRestart = async (executionId: string, fromNodeId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/debug/executions/${executionId}/restart?from_node_id=${fromNodeId}&tenant_id=${tenantId}`, {
        method: "POST"
      });
      if (!res.ok) throw new Error("Failed to trigger execution restart");
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { triggerReplay, triggerRestart, loading, error };
}
