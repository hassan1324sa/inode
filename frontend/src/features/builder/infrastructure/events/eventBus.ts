import type { ExecutionEventDTO } from '../../../../shared/dto/workflow.dto';
import { useExecutionProjection } from '../projections/executionProjection';

export class ExecutionSession {
  private socket: WebSocket | null = null;
  private executionId: string;
  private onEvent: (event: ExecutionEventDTO) => void;
  private onCloseCallback: (session: ExecutionSession) => void;

  constructor(
    executionId: string,
    onEvent: (event: ExecutionEventDTO) => void,
    onClose: (session: ExecutionSession) => void
  ) {
    this.executionId = executionId;
    this.onEvent = onEvent;
    this.onCloseCallback = onClose;
  }

  public connect(): void {
    console.log(`[ExecutionSession] Connecting WebSocket to stream for execution: ${this.executionId}`);
    this.socket = new WebSocket(`ws://localhost:8000/api/v1/debug/ws?execution_id=${this.executionId}&tenant_id=tenant-a`);
    
    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Strict timestamp validation: ignore events without timestamp
        if (!data.timestamp) {
          console.warn('[ExecutionSession] Ignoring malformed event (missing timestamp):', data);
          return;
        }

        // Deterministic event ID mapping
        const eventId = data.event_id || `${data.execution_id}-${data.event_type}-${data.node_id || 'wf'}-${data.timestamp}`;

        this.onEvent({
          id: eventId,
          executionId: data.execution_id,
          type: data.event_type === 'NodeStarted' ? 'NODE_STARTED' :
                data.event_type === 'NodeCompleted' ? 'NODE_COMPLETED' :
                data.event_type === 'WorkflowCompleted' ? 'WORKFLOW_COMPLETED' :
                data.event_type === 'WorkflowFailed' ? 'WORKFLOW_FAILED' : data.event_type,
          nodeId: data.node_id,
          timestamp: data.timestamp,
          duration: data.payload?.duration || 0,
          output: data.payload || {},
          error: data.payload?.error,
        });
      } catch (err) {
        console.error('[ExecutionSession] Error parsing WebSocket message:', err);
      }
    };

    this.socket.onerror = (err) => {
      console.error('[ExecutionSession] WebSocket connection error:', err);
      this.disconnect();
    };

    this.socket.onclose = () => {
      console.log('[ExecutionSession] WebSocket connection closed.');
      this.disconnect();
    };
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
    this.onCloseCallback(this);
  }
}

export class EventBus {
  private activeSessions = new Map<string, ExecutionSession>();

  public listenToExecution(executionId: string) {
    // Disconnect existing session if present to prevent WebSocket leaks
    const existing = this.activeSessions.get(executionId);
    if (existing) {
      existing.disconnect();
    }

    const projection = useExecutionProjection.getState();
    projection.setActiveExecution(executionId);
    
    // Clear state before run
    projection.updateSnapshot(executionId, {
      status: 'Running',
      progressPercentage: 10,
      logs: ['Starting Temporal orchestration worker...'],
      completedNodes: [],
    });

    const session = new ExecutionSession(
      executionId,
      (event) => this.handleEvent(event),
      (s) => {
        // Identity-safe session deletion
        if (this.activeSessions.get(executionId) === s) {
          this.activeSessions.delete(executionId);
        }
      }
    );

    this.activeSessions.set(executionId, session);
    session.connect();
  }

  private handleEvent(event: ExecutionEventDTO) {
    const projection = useExecutionProjection.getState();
    const snapshot = projection.snapshots[event.executionId];
    
    // Terminal Guard: prevent state/status regression
    if (snapshot && (snapshot.status === 'Completed' || snapshot.status === 'Failed')) {
      console.log(`[EventBus] Ignoring event for finished execution ${event.executionId}`);
      return;
    }

    const logs = [...(snapshot?.logs || [])];
    const completedNodes = [...(snapshot?.completedNodes || [])];
    
    let status = snapshot?.status || 'Running';
    let progressPercentage = snapshot?.progressPercentage || 10;

    const variables = { ...(snapshot?.variables || {}) };
    
    // Resolve startedAt from event timeline
    let startedAt = snapshot?.startedAt;
    if (event.type === 'NODE_STARTED' && !startedAt) {
      startedAt = event.timestamp;
    }
    if (!startedAt && event.timestamp) {
      startedAt = event.timestamp;
    }

    // Compute execution duration from event timeline timestamps
    let duration = snapshot?.duration || 0;
    if (startedAt && event.timestamp) {
      const startTime = new Date(startedAt).getTime();
      const eventTime = new Date(event.timestamp).getTime();
      if (!isNaN(startTime) && !isNaN(eventTime)) {
        duration = Math.max(0, Math.round((eventTime - startTime) / 1000));
      }
    }

    if (event.type === 'NODE_STARTED') {
      logs.push(`Step ${event.nodeId} started execution.`);
      progressPercentage = Math.min(progressPercentage + 20, 80);
    } else if (event.type === 'NODE_COMPLETED') {
      logs.push(`Step ${event.nodeId} completed successfully in ${event.duration}s.`);
      if (event.nodeId) {
        completedNodes.push(event.nodeId);
      }
      if (event.output) {
        Object.assign(variables, event.output);
      }
      progressPercentage = Math.min(progressPercentage + 30, 90);
    } else if (event.type === 'WORKFLOW_COMPLETED') {
      logs.push(`Orchestration finished in ${duration}s.`);
      status = 'Completed';
      progressPercentage = 100;
    } else if (event.type === 'WORKFLOW_FAILED') {
      logs.push(`Orchestration failed: ${event.error}`);
      status = 'Failed';
    }

    projection.updateSnapshot(event.executionId, {
      status,
      completedNodes,
      logs,
      variables,
      progressPercentage,
      duration,
      startedAt,
    });

    // Close session when execution reaches terminal state
    if (status === 'Completed' || status === 'Failed') {
      const session = this.activeSessions.get(event.executionId);
      if (session) {
        session.disconnect();
      }
    }
  }
}

export const eventBusInstance = new EventBus();
