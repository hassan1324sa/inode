import { Workflow } from '../../domain/models/workflow';
import type { WorkflowId } from '../../domain/models/workflow';
import type { WorkflowRepository } from '../../application/repositories/workflowRepository';
import type { WorkflowDTO } from '../../../../shared/dto/workflow.dto';



export class FetchWorkflowRepository implements WorkflowRepository {
  private backendUrl = 'http://localhost:8000/api/v1';

  public async getById(id: WorkflowId): Promise<Workflow> {
    try {
      const res = await fetch(`${this.backendUrl}/workflows/${id}`);
      if (!res.ok) throw new Error('Failed to fetch workflow');
      const data: WorkflowDTO = await res.json();
      return this.mapToDomain(data);
    } catch {
      // Fallback local storage mock if backend offline
      const local = localStorage.getItem(`workflow_${id}`);
      if (local) {
        return this.mapToDomain(JSON.parse(local));
      }
      throw new Error(`Workflow ${id} not found.`);
    }
  }

  public async save(entity: Workflow): Promise<void> {
    const dto: WorkflowDTO = {
      formatVersion: entity.formatVersion,
      engineVersion: entity.engineVersion,
      nodeRegistryVersion: entity.nodeRegistryVersion,
      workflowVersion: entity.workflowVersion,
      metadata: entity.metadata,
      variables: entity.variables,
      nodes: entity.nodes,
      edges: entity.edges,
    };
    
    // Save locally
    localStorage.setItem(`workflow_${entity.metadata.id}`, JSON.stringify(dto));

    try {
      await fetch(`${this.backendUrl}/workflows/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dto),
      });
    } catch (e) {
      console.warn('Backend offline, saved locally to LocalStorage', e);
    }
  }

  public async delete(id: WorkflowId): Promise<void> {
    localStorage.removeItem(`workflow_${id}`);
  }

  public async list(): Promise<Workflow[]> {
    try {
      const res = await fetch(`${this.backendUrl}/workflows/`);
      if (!res.ok) throw new Error('Failed to list workflows');
      const data: WorkflowDTO[] = await res.json();
      return data.map(this.mapToDomain);
    } catch {
      return [];
    }
  }

  private mapToDomain(dto: WorkflowDTO): Workflow {
    return new Workflow(
      dto.formatVersion,
      dto.engineVersion,
      dto.nodeRegistryVersion,
      dto.workflowVersion,
      dto.metadata,
      dto.nodes,
      dto.edges,
      dto.variables
    );
  }
}
export const workflowRepositoryInstance = new FetchWorkflowRepository();
