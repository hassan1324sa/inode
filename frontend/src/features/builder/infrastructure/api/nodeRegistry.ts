import type { NodePlugin } from '../../domain/plugins/plugin';


export class FetchNodeRegistry {
  private plugins: Map<string, NodePlugin> = new Map();

  constructor() {
    this.registerDefaultPlugins();
  }

  public async getPlugins(): Promise<Map<string, NodePlugin>> {
    return this.plugins;
  }

  private registerDefaultPlugins() {
    // 1. Set Variable Node
    this.plugins.set('set_variable', {
      metadata: {
        id: 'set_variable',
        name: 'Set Variable',
        category: 'Variables',
        description: 'Set a variable inside the execution scope',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['set', 'var', 'assign'],
      },
      capabilities: {
        trigger: false,
        async: false,
        streaming: false,
        retryable: false,
        credentialRequired: false,
      },
      schema: {
        version: 1,
        fields: [
          { name: 'variable_name', label: 'Variable Name', type: 'text', required: true, defaultValue: 'my_var' },
          { name: 'variable_value', label: 'Variable Value', type: 'text', required: true, defaultValue: '' },
        ],
      },
      icon: 'Variable',
      color: '#A855F7',
      defaultData: () => ({ variable_name: 'my_var', variable_value: '42' }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.variable_name) errors.push('Variable Name is required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });

    // 2. HTTP Request Node
    this.plugins.set('http_request', {
      metadata: {
        id: 'http_request',
        name: 'HTTP Request',
        category: 'HTTP',
        description: 'Make an external HTTP REST call',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['api', 'fetch', 'curl', 'request'],
      },
      capabilities: {
        trigger: false,
        async: true,
        streaming: false,
        retryable: true,
        credentialRequired: false,
      },
      schema: {
        version: 1,
        fields: [
          {
            name: 'method',
            label: 'Method',
            type: 'select',
            required: true,
            defaultValue: 'GET',
            options: [
              { label: 'GET', value: 'GET' },
              { label: 'POST', value: 'POST' },
              { label: 'PUT', value: 'PUT' },
              { label: 'DELETE', value: 'DELETE' },
            ],
          },
          { name: 'url', label: 'URL', type: 'text', required: true, defaultValue: 'https://api.example.com/v1' },
          { name: 'headers', label: 'Headers (JSON)', type: 'textarea', defaultValue: '{}' },
          { name: 'body', label: 'Body (JSON)', type: 'textarea', defaultValue: '{}' },
        ],
      },
      icon: 'Globe',
      color: '#3B82F6',
      defaultData: () => ({ method: 'GET', url: 'https://api.example.com/v1', headers: '{}', body: '{}' }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.url) errors.push('URL is required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });

    // 3. AI Agent Node
    this.plugins.set('ai_agent', {
      metadata: {
        id: 'ai_agent',
        name: 'AI Agent',
        category: 'AI',
        description: 'Execute prompt generation with Gemini or OpenAI models',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['gpt', 'gemini', 'prompt', 'llm', 'chat'],
      },
      capabilities: {
        trigger: false,
        async: true,
        streaming: true,
        retryable: true,
        credentialRequired: true,
      },
      schema: {
        version: 1,
        fields: [
          {
            name: 'model',
            label: 'Model',
            type: 'select',
            required: true,
            defaultValue: 'gemini-1.5-flash',
            options: [
              { label: 'Gemini 1.5 Flash', value: 'gemini-1.5-flash' },
              { label: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro' },
              { label: 'GPT-4o', value: 'gpt-4o' },
            ],
          },
          { name: 'prompt', label: 'System Instructions / Prompt', type: 'textarea', required: true, defaultValue: '' },
          { name: 'credentialId', label: 'Credentials', type: 'secret', required: true },
        ],
      },
      icon: 'Cpu',
      color: '#10B981',
      defaultData: () => ({ model: 'gemini-1.5-flash', prompt: 'Summarize the input', credentialId: '' }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.prompt) errors.push('Prompt is required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });
  }
}
export const nodeRegistryInstance = new FetchNodeRegistry();
