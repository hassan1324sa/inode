import { create } from 'zustand';
import type { ExecutionSnapshotDTO } from '../../../../shared/dto/workflow.dto';


interface ExecutionState {
  snapshots: Record<string, ExecutionSnapshotDTO>;
  activeExecutionId: string | null;
  liveLogs: string[];

  updateSnapshot: (executionId: string, snapshot: Partial<ExecutionSnapshotDTO>) => void;
  setActiveExecution: (executionId: string | null) => void;
  addLog: (log: string) => void;
  clearLogs: () => void;
}

export const useExecutionProjection = create<ExecutionState>((set) => ({
  snapshots: {},
  activeExecutionId: null,
  liveLogs: [],

  updateSnapshot: (executionId, snapshot) => set((state) => {
    const existing = state.snapshots[executionId] || {
      id: executionId,
      workflowId: '',
      status: 'Queued',
      completedNodes: [],
      pendingNodes: [],
      variables: {},
      logs: [],
      startedAt: new Date().toISOString(),
      duration: 0,
      progressPercentage: 0,
    };
    return {
      snapshots: {
        ...state.snapshots,
        [executionId]: { ...existing, ...snapshot } as ExecutionSnapshotDTO,
      },
    };
  }),
  setActiveExecution: (executionId) => set({ activeExecutionId: executionId, liveLogs: [] }),
  addLog: (log) => set((state) => ({ liveLogs: [...state.liveLogs, log] })),
  clearLogs: () => set({ liveLogs: [] }),
}));
