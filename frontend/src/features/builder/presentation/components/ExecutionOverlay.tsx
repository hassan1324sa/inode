import React from "react";
import type { ExecutionEvent } from "../hooks/useExecutionStream";

interface ExecutionOverlayProps {
  status: "connecting" | "connected" | "disconnected";
  events: ExecutionEvent[];
}

export const ExecutionOverlay: React.FC<ExecutionOverlayProps> = ({ status, events }) => {
  return (
    <div className="absolute top-4 right-4 bg-zinc-900 border border-zinc-800 rounded-lg p-4 shadow-lg w-80 text-white z-50">
      <div className="flex items-center justify-between mb-3 border-b border-zinc-800 pb-2">
        <span className="font-semibold text-sm">Execution Stream</span>
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${
            status === "connected" ? "bg-green-500" : status === "connecting" ? "bg-yellow-500 animate-pulse" : "bg-red-500"
          }`} />
          <span className="text-xs uppercase text-zinc-400">{status}</span>
        </div>
      </div>
      <div className="max-h-48 overflow-y-auto space-y-1 text-xs">
        {events.length === 0 ? (
          <span className="text-zinc-500 italic block text-center py-2">No events streamed yet</span>
        ) : (
          events.map((e) => (
            <div key={e.event_id} className="p-1.5 hover:bg-zinc-800 rounded transition flex flex-col gap-0.5">
              <div className="flex justify-between text-zinc-400">
                <span className="font-medium text-[10px] text-indigo-400">#{e.sequence}</span>
                <span>{new Date(e.timestamp * 1000).toLocaleTimeString()}</span>
              </div>
              <div className="font-semibold text-zinc-200">{e.event_type}</div>
              {e.node_id && <div className="text-[10px] text-zinc-400">Node: {e.node_id}</div>}
              {e.payload && Object.keys(e.payload).length > 0 && (
                <pre className="text-[9px] text-zinc-500 bg-black/30 p-1 rounded overflow-x-auto mt-1 max-h-16">
                  {JSON.stringify(e.payload, null, 2)}
                </pre>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
