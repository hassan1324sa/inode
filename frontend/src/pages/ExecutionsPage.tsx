import React from 'react';
import * as Icons from 'lucide-react';
import { useExecutionProjection } from '../features/builder/application/services';

export const ExecutionsPage: React.FC = () => {
  const { snapshots, activeExecutionId, liveLogs, setActiveExecution } = useExecutionProjection();

  const snapshotList = Object.values(snapshots);

  const activeSnapshot = activeExecutionId ? snapshots[activeExecutionId] : null;

  return (
    <div className="flex-1 h-full flex overflow-hidden bg-background text-left">
      {/* Runs history list sidebar */}
      <aside className="w-[300px] border-r border-border glass flex flex-col p-4 overflow-y-auto">
        <div className="flex items-center gap-2 mb-4">
          <Icons.Activity className="text-primary" size={18} />
          <h3 className="font-bold text-sm text-foreground">Runs History</h3>
        </div>

        <div className="space-y-2">
          {snapshotList.map((snap) => (
            <button
              key={snap.id}
              onClick={() => setActiveExecution(snap.id)}
              className={`w-full p-3 rounded-lg border text-left transition-all duration-150 ${
                activeExecutionId === snap.id
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-background/20 hover:bg-background/40'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-mono text-muted-foreground">{snap.id}</span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                  snap.status === 'Completed' ? 'bg-emerald-500/20 text-emerald-400' :
                  snap.status === 'Failed' ? 'bg-red-500/20 text-red-400' :
                  'bg-blue-500/20 text-blue-400 animate-pulse'
                }`}>
                  {snap.status}
                </span>
              </div>
              <div className="text-[10px] text-muted-foreground">Started: {new Date(snap.startedAt).toLocaleTimeString()}</div>
              
              {/* Progress bar */}
              <div className="w-full bg-border/40 h-1 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-primary h-full transition-all duration-300"
                  style={{ width: `${snap.progressPercentage}%` }}
                />
              </div>
            </button>
          ))}
          {snapshotList.length === 0 && (
            <div className="text-center py-8 text-xs text-muted-foreground">No execution runs yet. Press "Run" in builder to start.</div>
          )}
        </div>
      </aside>

      {/* Detail viewer */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {activeSnapshot ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Header info */}
            <header className="px-6 py-4 border-b border-border glass flex items-center justify-between">
              <div>
                <h2 className="font-bold text-sm text-foreground m-0">Run Details: {activeSnapshot.id}</h2>
                <p className="text-[10px] text-muted-foreground">Status: {activeSnapshot.status} | Progress: {activeSnapshot.progressPercentage}%</p>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <span className="text-[10px] text-muted-foreground block">Duration</span>
                  <span className="text-xs font-semibold text-foreground">{activeSnapshot.duration}s</span>
                </div>
              </div>
            </header>

            {/* Run details split layout */}
            <div className="flex-1 flex overflow-hidden p-6 gap-6">
              {/* Logs panel */}
              <section className="flex-1 border border-border rounded-lg bg-slate-950/40 p-4 flex flex-col overflow-hidden glass">
                <div className="flex items-center justify-between pb-3 border-b border-border/50 mb-3">
                  <span className="text-xs font-bold text-foreground">Terminal Logs</span>
                  <Icons.Terminal size={14} className="text-muted-foreground" />
                </div>
                <div className="flex-1 overflow-y-auto font-mono text-[11px] text-slate-300 space-y-1.5 scrollbar-thin">
                  {liveLogs.length > 0 ? (
                    liveLogs.map((log, i) => (
                      <div key={i} className="flex gap-2">
                        <span className="text-muted-foreground select-none">[{i + 1}]</span>
                        <span>{log}</span>
                      </div>
                    ))
                  ) : (
                    activeSnapshot.logs.map((log, i) => (
                      <div key={i} className="flex gap-2">
                        <span className="text-muted-foreground select-none">[{i + 1}]</span>
                        <span>{log}</span>
                      </div>
                    ))
                  )}
                </div>
              </section>

              {/* Steps overview panel */}
              <section className="w-[320px] border border-border rounded-lg bg-slate-950/40 p-4 flex flex-col overflow-hidden glass">
                <div className="flex items-center justify-between pb-3 border-b border-border/50 mb-3">
                  <span className="text-xs font-bold text-foreground">Executed Nodes</span>
                  <Icons.Workflow size={14} className="text-muted-foreground" />
                </div>
                <div className="flex-1 overflow-y-auto space-y-3">
                  {activeSnapshot.completedNodes.map((nodeId) => (
                    <div key={nodeId} className="flex items-center justify-between p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-md">
                      <div className="flex items-center gap-2">
                        <Icons.CheckCircle size={14} className="text-emerald-400" />
                        <span className="text-xs font-semibold text-foreground">{nodeId}</span>
                      </div>
                      <span className="text-[10px] text-emerald-400">Completed</span>
                    </div>
                  ))}
                  {activeSnapshot.status === 'Running' && (
                    <div className="flex items-center justify-between p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-md animate-pulse">
                      <div className="flex items-center gap-2">
                        <Icons.Loader size={14} className="text-blue-400 animate-spin" />
                        <span className="text-xs font-semibold text-foreground">Processing Node...</span>
                      </div>
                    </div>
                  )}
                  {activeSnapshot.completedNodes.length === 0 && activeSnapshot.status !== 'Running' && (
                    <div className="text-center py-8 text-xs text-muted-foreground">No executed nodes.</div>
                  )}
                </div>
              </section>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground text-xs">
            <Icons.MonitorPlay className="mb-2 opacity-50" size={32} />
            Select an execution run from the left history to view detailed trace details.
          </div>
        )}
      </main>
    </div>
  );
};
export default ExecutionsPage;
