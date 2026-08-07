import React, { useState } from "react";
import { useExecutionDiff } from "../hooks/useExecutionDiff";

interface ExecutionDiffProps {
  executionId: string;
  organizationId: string;
}

export const ExecutionDiff: React.FC<ExecutionDiffProps> = ({ executionId, organizationId }) => {
  const [compareId, setCompareId] = useState("");
  const { diff, fetchDiff, loading, error } = useExecutionDiff(organizationId);

  const handleCompare = () => {
    if (!compareId) return;
    fetchDiff(executionId, compareId).catch((err) => {
      console.error(err);
    });
  };

  return (
    <div className="fixed sm:absolute top-16 sm:top-20 right-4 left-4 sm:left-auto bg-zinc-900 border border-zinc-800 rounded-lg p-4 shadow-xl w-auto sm:w-80 max-w-full text-white z-50 text-xs transition-all">
      <div className="font-semibold text-sm mb-3 border-b border-zinc-800 pb-2">
        Execution Diff Analyzer
      </div>
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          placeholder="Compare Execution ID"
          value={compareId}
          onChange={(e) => setCompareId(e.target.value)}
          className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
        />
        <button
          onClick={handleCompare}
          disabled={loading || !compareId}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-2.5 py-1 rounded text-xs transition"
        >
          Compare
        </button>
      </div>
      {loading && <div className="text-center py-4 text-zinc-500 animate-pulse">Calculating difference...</div>}
      {error && <div className="text-red-400 mb-2">Error: {error}</div>}
      {diff && (
        <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
          {/* Structural Diff */}
          <div>
            <div className="font-semibold text-zinc-300 border-b border-zinc-800 pb-1 mb-1">
              Structure Diff
            </div>
            {diff.workflow_structure_diff.added_nodes.length > 0 && (
              <div className="text-green-400">Added: {diff.workflow_structure_diff.added_nodes.join(", ")}</div>
            )}
            {diff.workflow_structure_diff.removed_nodes.length > 0 && (
              <div className="text-red-400">Removed: {diff.workflow_structure_diff.removed_nodes.join(", ")}</div>
            )}
            {diff.workflow_structure_diff.added_nodes.length === 0 &&
              diff.workflow_structure_diff.removed_nodes.length === 0 && (
                <div className="text-zinc-500 italic text-[11px]">No structural changes</div>
              )}
          </div>
          {/* Node Status Diff */}
          <div>
            <div className="font-semibold text-zinc-300 border-b border-zinc-800 pb-1 mb-1">
              Node Execution Status Diff
            </div>
            {Object.entries(diff.node_execution_diff).map(([nodeId, val]) => (
              <div key={nodeId} className="flex justify-between py-0.5 border-b border-zinc-800/40 text-[11px]">
                <span className="text-indigo-400">{nodeId}</span>
                <span className="text-zinc-400">
                  {val.before} ➔ <span className="text-zinc-200 font-semibold">{val.after}</span>
                </span>
              </div>
            ))}
            {Object.keys(diff.node_execution_diff).length === 0 && (
              <div className="text-zinc-500 italic text-[11px]">No status differences</div>
            )}
          </div>
          {/* Variables Diff */}
          <div>
            <div className="font-semibold text-zinc-300 border-b border-zinc-800 pb-1 mb-1">
              Variable Values Diff
            </div>
            {Object.entries(diff.state_variable_diff).map(([vName, val]) => (
              <div key={vName} className="p-1 bg-zinc-800/40 rounded border border-zinc-800/55 text-[11px] mb-1">
                <div className="text-indigo-400 font-medium">{vName}</div>
                <div className="text-red-400/80 line-through">Before: {JSON.stringify(val.before)}</div>
                <div className="text-green-400/90 font-semibold">After: {JSON.stringify(val.after)}</div>
              </div>
            ))}
            {Object.keys(diff.state_variable_diff).length === 0 && (
              <div className="text-zinc-500 italic text-[11px]">No variable differences</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
