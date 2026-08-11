import { Workflow } from '../../domain/models/workflow';
import type { WorkflowId } from '../../domain/models/workflow';
import type { WorkflowRepository } from '../../application/repositories/workflowRepository';
import type { WorkflowDTO } from '../../../../shared/dto/workflow.dto';
import { AppError } from '../../../../shared/errors/AppError';
import { authenticatedFetch, parseApiResponse } from '../../../../shared/api/authenticatedFetch';

export class FetchWorkflowRepository implements WorkflowRepository {
  private backendUrl = '/api/v1';

  public async getById(id: WorkflowId): Promise<Workflow> {
    try {
      const res = await authenticatedFetch(`${this.backendUrl}/workflows/${id}`);
      
      if (!res.ok) {
        // Genuine 404 from backend: throw NOT_FOUND error. Must NOT fallback to cache.
        if (res.status === 404) {
          throw AppError.fromHttpResponse(404, `Workflow with ID "${id}" was not found.`);
        }
        let errMessage: string | undefined;
        try {
          const body = await res.json();
          errMessage = body.message || body.detail;
        } catch {
          // ignore json parse error
        }
        throw AppError.fromHttpResponse(res.status, errMessage || `Backend returned error HTTP ${res.status}`);
      }

      const data: WorkflowDTO = await res.json();
      const domainModel = this.mapToDomain(data);
      
      // Update local storage cache on successful backend fetch
      try {
        localStorage.setItem(`workflow_${id}`, JSON.stringify(data));
      } catch {
        // Ignore local storage errors (e.g. quota exceeded)
      }

      return domainModel;
    } catch (err: any) {
      // If it's already an explicit AppError with 404 NOT_FOUND, rethrow immediately
      if (err instanceof AppError && err.kind === 'NOT_FOUND') {
        throw err;
      }

      // Network / Offline / Timeout failure handling: Fallback to local cache if available
      const local = localStorage.getItem(`workflow_${id}`);
      if (local) {
        try {
          return this.mapToDomain(JSON.parse(local));
        } catch {
          // Invalid cached payload
        }
      }

      // If network error and no cache found, throw typed network error
      if (err instanceof AppError) {
        throw err;
      }
      throw AppError.network(`Unable to connect to backend and no local cached state found for workflow "${id}".`);
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

    let res: Response;
    try {
      res = await authenticatedFetch(`${this.backendUrl}/workflows/${entity.metadata.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dto),
      });
    } catch {
      throw AppError.network('Failed to save workflow: Backend service is unreachable.');
    }

    if (!res.ok) {
      let errMessage: string | undefined;
      try {
        const body = await res.json();
        errMessage = body.message || body.detail;
      } catch {
        // ignore json parse error
      }
      throw AppError.fromHttpResponse(res.status, errMessage || `Failed to save workflow. Server status: ${res.status}`);
    }

    // SUCCESS ONLY: Update local cache AFTER backend confirms save
    try {
      localStorage.setItem(`workflow_${entity.metadata.id}`, JSON.stringify(dto));
    } catch {
      // Ignore quota issues
    }
  }

  public async delete(id: WorkflowId): Promise<void> {
    let res: Response;
    try {
      res = await authenticatedFetch(`${this.backendUrl}/workflows/${id}`, {
        method: 'DELETE',
      });
    } catch {
      throw AppError.network(`Failed to delete workflow "${id}": Backend service is unreachable.`);
    }

    if (!res.ok) {
      let errMessage: string | undefined;
      try {
        const body = await res.json();
        errMessage = body.message || body.detail;
      } catch {
        // ignore
      }
      throw AppError.fromHttpResponse(res.status, errMessage || `Failed to delete workflow "${id}". Status: ${res.status}`);
    }

    // SUCCESS ONLY: Remove from local cache after backend deletion succeeds
    localStorage.removeItem(`workflow_${id}`);
  }

  public async list(): Promise<Workflow[]> {
    try {
      const res = await authenticatedFetch(`${this.backendUrl}/workflows/`);
      if (!res.ok) {
        throw AppError.fromHttpResponse(res.status, 'Failed to retrieve workflow list from backend.');
      }
      const data: WorkflowDTO[] = await parseApiResponse(res);
      return data.map((dto) => this.mapToDomain(dto));
    } catch (err: any) {
      if (err instanceof AppError) throw err;
      throw AppError.network('Failed to list workflows: Backend unavailable.');
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

