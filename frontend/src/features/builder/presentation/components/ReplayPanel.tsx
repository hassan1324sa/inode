import React from "react";
import { useReplay } from "../hooks/useReplay";
import { useToast } from "../../../../shared/components/Toast";

interface ReplayPanelProps {
  executionId: string;
  organizationId: string;
  selectedNodeId: string | null;
}

export const ReplayPanel: React.FC<ReplayPanelProps> = ({ executionId, organizationId, selectedNodeId }) => {
  const { triggerReplay, triggerRestart, loading, error } = useReplay(organizationId);
  const { showToast } = useToast();

  const handleReplay = async () => {
    try {
      const res = await triggerReplay(executionId);
      showToast(`Deterministic Replay triggered successfully! New ID: ${res.replay_execution_id}`, 'success');
    } catch (err: any) {
      showToast(`Error triggering Replay: ${err.message}`, 'error');
    }
  };

  const handleRestart = async () => {
    if (!selectedNodeId) return;
    try {
      const res = await triggerRestart(executionId, selectedNodeId);
      showToast(`Restart from Node ${selectedNodeId} triggered successfully! New ID: ${res.new_execution_id}`, 'success');
    } catch (err: any) {
      showToast(`Error triggering Restart: ${err.message}`, 'error');
    }
  };

  return (
    <div className="fixed sm:absolute top-16 sm:top-20 left-4 right-4 sm:right-auto bg-zinc-900 border border-zinc-800 rounded-lg p-3 shadow-xl w-auto sm:w-64 max-w-full text-white z-50 text-xs transition-all">
      <div className="font-semibold text-xs mb-2 border-b border-zinc-800 pb-1.5 flex justify-between items-center">
        <span>Execution Control</span>
        {loading && <span className="text-[10px] text-yellow-500 animate-pulse">invoking...</span>}
      </div>
      <div className="space-y-2">
        <button
          onClick={handleReplay}
          disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-1 px-2 rounded text-center transition"
        >
          Replay Entire Execution
        </button>
        <div className="border-t border-zinc-800 my-1 pt-1.5">
          <div className="text-zinc-400 mb-1">
            Restart from node: <span className="font-semibold text-zinc-200">{selectedNodeId || "None selected"}</span>
          </div>
          <button
            onClick={handleRestart}
            disabled={loading || !selectedNodeId}
            className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium py-1 px-2 rounded text-center transition"
          >
            Restart from Node
          </button>
        </div>
        {error && <div className="text-[10px] text-red-400 mt-1">Error: {error}</div>}
      </div>
    </div>
  );
};
