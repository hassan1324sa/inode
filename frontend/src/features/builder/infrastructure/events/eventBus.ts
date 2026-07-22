import type { ExecutionEventDTO } from '../../../../shared/dto/workflow.dto';
import { useExecutionProjection } from '../projections/executionProjection';


export interface EventTransport {
  connect(executionId: string): void;
  disconnect(): void;
  subscribe(callback: (event: ExecutionEventDTO) => void): void;
}

export class MockTransport implements EventTransport {
  private callback: ((event: ExecutionEventDTO) => void) | null = null;
  private intervalId: any = null;

  public connect(executionId: string): void {
    console.log(`[EventTransport] Mock connecting to stream for execution: ${executionId}`);
    
    // Simulate streaming execution events for the AI enrichment scenario
    const steps = [
      { type: 'NODE_STARTED', nodeId: 'node-set-variable', duration: 0 },
      { type: 'NODE_COMPLETED', nodeId: 'node-set-variable', duration: 0.1, output: { variable_name: 'customer_email', variable_value: 'lead@corporate.com' } },
      
      { type: 'NODE_STARTED', nodeId: 'node-http-request', duration: 0 },
      { type: 'NODE_COMPLETED', nodeId: 'node-http-request', duration: 1.4, output: { status: 200, lead_score: 95, company: 'Corporate Inc' } },
      
      { type: 'NODE_STARTED', nodeId: 'node-ai-agent', duration: 0 },
      { type: 'NODE_COMPLETED', nodeId: 'node-ai-agent', duration: 2.1, output: { generated_proposal: 'Dear Corporate Inc, we noticed your team...' } },
      
      { type: 'WORKFLOW_COMPLETED', duration: 3.6 }
    ];

    
    let stepIndex = 0;
    this.intervalId = setInterval(() => {
      if (stepIndex >= steps.length) {
        this.disconnect();
        return;
      }
      
      const current = steps[stepIndex++];
      if (this.callback) {
        this.callback({
          id: Math.random().toString(36).substr(2, 9),
          executionId,
          type: current.type,
          nodeId: current.nodeId,
          timestamp: new Date().toISOString(),
          duration: current.duration,
          output: current.output,
        });
      }
    }, 2000);
  }

  public disconnect(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  public subscribe(callback: (event: ExecutionEventDTO) => void): void {
    this.callback = callback;
  }
}

export class EventBus {
  private transport: EventTransport;

  constructor(transport: EventTransport) {
    this.transport = transport;
  }

  public listenToExecution(executionId: string) {
    const projection = useExecutionProjection.getState();
    projection.setActiveExecution(executionId);
    
    // Clear state before run
    projection.updateSnapshot(executionId, {
      status: 'Running',
      progressPercentage: 10,
      logs: ['Starting Temporal orchestration worker...'],
      completedNodes: [],
    });

    this.transport.subscribe((event) => {
      this.handleEvent(event);
    });
    this.transport.connect(executionId);
  }

  private handleEvent(event: ExecutionEventDTO) {
    const projection = useExecutionProjection.getState();
    const snapshot = projection.snapshots[event.executionId];
    
    const logs = [...(snapshot?.logs || [])];
    const completedNodes = [...(snapshot?.completedNodes || [])];
    
    let status = snapshot?.status || 'Running';
    let progressPercentage = snapshot?.progressPercentage || 10;

    if (event.type === 'NODE_STARTED') {
      logs.push(`Step ${event.nodeId} started execution.`);
      progressPercentage = Math.min(progressPercentage + 20, 80);
    } else if (event.type === 'NODE_COMPLETED') {
      logs.push(`Step ${event.nodeId} completed successfully in ${event.duration}s.`);
      if (event.nodeId) {
        completedNodes.push(event.nodeId);
      }
      progressPercentage = Math.min(progressPercentage + 30, 90);
    } else if (event.type === 'WORKFLOW_COMPLETED') {
      logs.push(`Orchestration finished in ${event.duration}s.`);
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
      progressPercentage,
    });
  }
}

export const eventBusInstance = new EventBus(new MockTransport());
