import type { Workflow, WorkflowId } from '../../domain/models/workflow';
import type { Repository } from './repository';


export interface WorkflowRepository extends Repository<Workflow, WorkflowId> {
  // Add workflow-specific application commands if needed
}
