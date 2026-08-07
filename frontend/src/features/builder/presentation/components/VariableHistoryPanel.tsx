import React, { useState } from "react";
import type { VariableChange } from "../hooks/useVariableHistory";

interface VariableHistoryPanelProps {
  variableHistory: Record<string, VariableChange[]>;
}

export const VariableHistoryPanel: React.FC<VariableHistoryPanelProps> = ({ variableHistory }) => {
  const [selectedVar, setSelectedVar] = useState<string | null>(null);

  return (
    <div className="fixed sm:absolute bottom-4 left-4 right-4 sm:right-auto bg-zinc-900 border border-zinc-800 rounded-lg p-4 shadow-xl w-auto sm:w-80 max-w-full text-white z-50 transition-all">
      <div className="font-semibold text-sm mb-3 border-b border-zinc-800 pb-2">
        Variable Mutations (Time Travel)
      </div>
      <div className="flex gap-2">
        <div className="w-1/3 border-r border-zinc-800 pr-2 space-y-1 overflow-y-auto max-h-40">
          {Object.keys(variableHistory).map((vName) => (
            <button
              key={vName}
              onClick={() => setSelectedVar(vName)}
              className={`w-full text-left p-1 text-xs rounded transition truncate ${
                selectedVar === vName ? "bg-indigo-600 text-white" : "hover:bg-zinc-800 text-zinc-400"
              }`}
            >
              {vName}
            </button>
          ))}
          {Object.keys(variableHistory).length === 0 && (
            <span className="text-[10px] text-zinc-500 italic">No variables changed</span>
          )}
        </div>
        <div className="w-2/3 pl-2 overflow-y-auto max-h-40 space-y-2 text-xs">
          {selectedVar ? (
            variableHistory[selectedVar].map((c) => (
              <div key={c.sequence} className="bg-zinc-800/50 p-1.5 rounded text-[11px] border border-zinc-800">
                <div className="flex justify-between text-zinc-400 text-[10px] mb-1">
                  <span>Seq #{c.sequence}</span>
                  {c.nodeId && <span className="text-indigo-400">Node: {c.nodeId}</span>}
                </div>
                <div className="line-through text-red-400 overflow-x-auto truncate">
                  Prev: {JSON.stringify(c.previousValue)}
                </div>
                <div className="text-green-400 font-semibold overflow-x-auto truncate">
                  Next: {JSON.stringify(c.currentValue)}
                </div>
              </div>
            ))
          ) : (
            <span className="text-zinc-500 italic block text-center py-4">Select a variable to inspect history</span>
          )}
        </div>
      </div>
    </div>
  );
};
