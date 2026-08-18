import React from 'react';
import * as Icons from 'lucide-react';
import { useExecutionProjection } from '../../infrastructure/projections/executionProjection';

export const TerminalConsole: React.FC = () => {
  const activeExecutionId = useExecutionProjection((state) => state.activeExecutionId);
  const activeSnapshot = useExecutionProjection((state) => 
    activeExecutionId ? state.snapshots[activeExecutionId] : null
  );

  const [isOpen, setIsOpen] = React.useState(true);
  const [filter, setFilter] = React.useState<'all' | 'info' | 'error' | 'warning'>('all');
  const bottomRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new logs
  React.useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activeSnapshot?.logs]);

  // Auto-open terminal when execution changes to active running state
  React.useEffect(() => {
    if (activeExecutionId) {
      setIsOpen(true);
    }
  }, [activeExecutionId]);

  if (!isOpen) {
    return (
      <div className="h-9 border-t border-border bg-slate-950 flex items-center justify-between px-6 z-20">
        <button 
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-bold font-mono transition-colors"
        >
          <Icons.Terminal size={14} className="text-primary" />
          <span>TERMINAL CONSOLE {activeExecutionId ? `[${activeExecutionId.substring(0,8)}]` : '[OFFLINE]'}</span>
        </button>
        {activeSnapshot && (
          <div className="flex items-center gap-2 text-[10px]">
            <span className={`w-2 h-2 rounded-full ${
              activeSnapshot.status === 'Completed' ? 'bg-emerald-500' : activeSnapshot.status === 'Failed' ? 'bg-red-500' : 'bg-amber-500 animate-pulse'
            }`} />
            <span className="text-muted-foreground uppercase font-semibold">{activeSnapshot.status}</span>
          </div>
        )}
      </div>
    );
  }

  const logs = activeSnapshot?.logs || [];
  const status = activeSnapshot?.status || 'Offline';

  const filteredLogs = logs.filter(log => {
    if (filter === 'all') return true;
    if (filter === 'error') return log.toLowerCase().includes('fail') || log.toLowerCase().includes('error');
    if (filter === 'warning') return log.toLowerCase().includes('warn') || log.toLowerCase().includes('skipping');
    if (filter === 'info') return !log.toLowerCase().includes('fail') && !log.toLowerCase().includes('error') && !log.toLowerCase().includes('warn');
    return true;
  });

  return (
    <div className="h-[240px] border-t border-slate-800 bg-[#0b0f19] flex flex-col z-20 shadow-[0_-8px_24px_rgba(0,0,0,0.6)] animate-in slide-in-from-bottom duration-300">
      {/* Header bar */}
      <div className="h-10 border-b border-slate-800 flex items-center justify-between px-6 bg-[#0e1424]">
        <div className="flex items-center gap-3">
          <Icons.Terminal size={14} className="text-primary animate-pulse" />
          <span className="text-xs font-bold font-mono text-slate-200">
            TERMINAL CONSOLE {activeExecutionId ? `[EXEC_ID: ${activeExecutionId}]` : ''}
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 font-mono">
            STATUS: {status.toUpperCase()}
          </span>
        </div>

        {/* Filter Toolbar */}
        <div className="flex items-center gap-2">
          <button 
            onClick={() => setFilter('all')} 
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${filter === 'all' ? 'bg-primary/20 text-primary border border-primary/30' : 'text-slate-400 hover:text-slate-200'}`}
          >
            ALL ({logs.length})
          </button>
          <button 
            onClick={() => setFilter('info')} 
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${filter === 'info' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-slate-400 hover:text-slate-200'}`}
          >
            INFO
          </button>
          <button 
            onClick={() => setFilter('warning')} 
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${filter === 'warning' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'text-slate-400 hover:text-slate-200'}`}
          >
            WARN
          </button>
          <button 
            onClick={() => setFilter('error')} 
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${filter === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'text-slate-400 hover:text-slate-200'}`}
          >
            ERR
          </button>

          <div className="w-[1px] h-4 bg-slate-800 mx-1" />
          
          <button 
            onClick={() => setIsOpen(false)}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Minimize"
          >
            <Icons.ChevronDown size={14} />
          </button>
        </div>
      </div>

      {/* Terminal stdout display screen */}
      <div className="flex-1 p-4 overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-300 space-y-1 bg-black/40">
        {filteredLogs.length === 0 ? (
          <div className="text-slate-500 italic py-6 text-center">
            {activeExecutionId ? 'Waiting for execution events...' : 'No active session. Click "Run" to trigger an execution.'}
          </div>
        ) : (
          filteredLogs.map((log, idx) => {
            const isError = log.toLowerCase().includes('fail') || log.toLowerCase().includes('error');
            const isWarning = log.toLowerCase().includes('warn') || log.toLowerCase().includes('skipping');
            const icon = isError ? '❌' : isWarning ? '⚠️' : 'ℹ️';
            const textColor = isError ? 'text-red-400 font-semibold' : isWarning ? 'text-amber-400 font-semibold' : 'text-emerald-400';

            return (
              <div key={idx} className="flex gap-2 items-start py-0.5 border-b border-slate-900/50 hover:bg-slate-900/20 px-2 rounded">
                <span className="text-[10px]">{icon}</span>
                <span className="text-slate-500 font-semibold select-none">inode_stdout:~$</span>
                <span className={`flex-1 break-all ${textColor}`}>{log}</span>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
export default TerminalConsole;
