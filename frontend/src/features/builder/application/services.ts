import { workflowRepositoryInstance } from '../infrastructure/api/workflowRepository';
import { nodeRegistryInstance } from '../infrastructure/api/nodeRegistry';
import { eventBusInstance } from '../infrastructure/events/eventBus';

export const workflowRepository = workflowRepositoryInstance;
export const nodeRegistry = nodeRegistryInstance;
export const eventBus = eventBusInstance;
export { useWorkflowProjection } from '../infrastructure/projections/workflowProjection';
export { useUIProjection } from '../infrastructure/projections/uiProjection';
export { useExecutionProjection } from '../infrastructure/projections/executionProjection';
export { HistoryManager } from './services/history';
export { BuildValidation, ExecutionValidation } from '../domain/validation/validation';

