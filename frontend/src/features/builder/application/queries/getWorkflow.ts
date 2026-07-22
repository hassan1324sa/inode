import type { QueryHandler } from './queryHandler';
import type { Workflow, WorkflowId } from '../../domain/models/workflow';
import { workflowRepository } from '../services';

export class GetWorkflowQuery {
  public readonly workflowId: WorkflowId;
  constructor(workflowId: WorkflowId) {
    this.workflowId = workflowId;
  }
}


export class GetWorkflowHandler implements QueryHandler<GetWorkflowQuery, Workflow> {
  public async execute(query: GetWorkflowQuery): Promise<Workflow> {
    return await workflowRepository.getById(query.workflowId);
  }
}
