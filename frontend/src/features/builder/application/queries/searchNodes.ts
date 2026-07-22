import type { QueryHandler } from './queryHandler';
import type { NodePlugin } from '../../domain/plugins/plugin';
import { nodeRegistry } from '../services';

export class SearchNodesQuery {
  public readonly searchTerm: string;
  constructor(searchTerm: string) {
    this.searchTerm = searchTerm;
  }
}


export class SearchNodesHandler implements QueryHandler<SearchNodesQuery, NodePlugin[]> {
  public async execute(query: SearchNodesQuery): Promise<NodePlugin[]> {
    const registry = await nodeRegistry.getPlugins();
    const list = Array.from(registry.values());
    
    if (!query.searchTerm) return list;

    const term = query.searchTerm.toLowerCase();
    return list.filter(plugin => 
      plugin.metadata.name.toLowerCase().includes(term) ||
      plugin.metadata.category.toLowerCase().includes(term) ||
      plugin.metadata.aliases?.some(alias => alias.toLowerCase().includes(term))
    );
  }
}
