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

    // 4. Webhook Trigger Node (Triggers)
    this.plugins.set('webhook_trigger', {
      metadata: {
        id: 'webhook_trigger',
        name: 'Webhook Trigger',
        category: 'Triggers',
        description: 'Trigger workflow execution when HTTP POST request is received',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['webhook', 'trigger', 'post', 'incoming'],
      },
      capabilities: { trigger: true, async: false, streaming: false, retryable: false, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'path', label: 'Webhook Path', type: 'text', required: true, defaultValue: '/webhook-1' },
          { name: 'method', label: 'HTTP Method', type: 'select', defaultValue: 'POST', options: [{ label: 'POST', value: 'POST' }, { label: 'GET', value: 'GET' }] },
        ],
      },
      icon: 'Zap',
      color: '#10B981',
      defaultData: () => ({ path: '/webhook-1', method: 'POST' }),
      validate: (data: any) => ({ isValid: !!data?.path, errors: data?.path ? [] : ['Webhook Path is required'] }),
      migrate: (_v, data) => data as any,
    });

    // 5. Schedule Trigger Node (Triggers)
    this.plugins.set('schedule_trigger', {
      metadata: {
        id: 'schedule_trigger',
        name: 'Schedule Trigger',
        category: 'Triggers',
        description: 'Execute workflow on a recurring Cron or interval schedule',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['cron', 'timer', 'schedule', 'interval'],
      },
      capabilities: { trigger: true, async: false, streaming: false, retryable: false, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'cronExpression', label: 'Cron Expression', type: 'text', required: true, defaultValue: '0 * * * *' },
        ],
      },
      icon: 'Clock',
      color: '#10B981',
      defaultData: () => ({ cronExpression: '0 * * * *' }),
      validate: (data: any) => ({ isValid: !!data?.cronExpression, errors: data?.cronExpression ? [] : ['Cron Expression required'] }),
      migrate: (_v, data) => data as any,
    });

    // 6. Slack Notification Node (Communication)
    this.plugins.set('slack_notification', {
      metadata: {
        id: 'slack_notification',
        name: 'Slack Notification',
        category: 'Communication',
        description: 'Send formatted message to a Slack channel',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['slack', 'chat', 'message', 'alert'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: true },
      schema: {
        version: 1,
        fields: [
          { name: 'channel', label: 'Channel', type: 'text', required: true, defaultValue: '#general' },
          { name: 'message', label: 'Message Body', type: 'textarea', required: true, defaultValue: 'Hello from Fluxa!' },
        ],
      },
      icon: 'MessageSquare',
      color: '#EC4899',
      defaultData: () => ({ channel: '#general', message: 'Hello from Fluxa!' }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.channel) errors.push('Channel required');
        if (!data?.message) errors.push('Message required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });

    // 7. IF Condition Node (Logic)
    this.plugins.set('if_condition', {
      metadata: {
        id: 'if_condition',
        name: 'IF Condition',
        category: 'Logic',
        description: 'Branch workflow execution based on variable or expression test',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['if', 'condition', 'branch', 'switch'],
      },
      capabilities: { trigger: false, async: false, streaming: false, retryable: false, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'expression', label: 'Condition Expression', type: 'text', required: true, defaultValue: 'status == "success"' },
        ],
      },
      icon: 'GitBranch',
      color: '#F59E0B',
      defaultData: () => ({ expression: 'status == "success"' }),
      validate: (data: any) => ({ isValid: !!data?.expression, errors: data?.expression ? [] : ['Expression required'] }),
      migrate: (_v, data) => data as any,
    });

    // 8. Transform JSON Node (Data)
    this.plugins.set('transform_json', {
      metadata: {
        id: 'transform_json',
        name: 'Transform JSON',
        category: 'Data',
        description: 'Map, filter, and restructure JSON payloads using jq/expressions',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['json', 'transform', 'map', 'jq'],
      },
      capabilities: { trigger: false, async: false, streaming: false, retryable: false, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'query', label: 'Transform Query', type: 'text', required: true, defaultValue: '.data | map({id, name})' },
        ],
      },
      icon: 'FileJson',
      color: '#06B6D4',
      defaultData: () => ({ query: '.data | map({id, name})' }),
      validate: (data: any) => ({ isValid: !!data?.query, errors: data?.query ? [] : ['Query required'] }),
      migrate: (_v, data) => data as any,
    });

    // 9. Read/Write File Node (Files)
    this.plugins.set('file_storage', {
      metadata: {
        id: 'file_storage',
        name: 'File Storage',
        category: 'Files',
        description: 'Read or write files from cloud storage or local volume',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['file', 'read', 'write', 's3', 'storage'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'operation', label: 'Operation', type: 'select', defaultValue: 'read', options: [{ label: 'Read File', value: 'read' }, { label: 'Write File', value: 'write' }] },
          { name: 'filePath', label: 'File Path', type: 'text', required: true, defaultValue: '/data/output.json' },
        ],
      },
      icon: 'Folder',
      color: '#6366F1',
      defaultData: () => ({ operation: 'read', filePath: '/data/output.json' }),
      validate: (data: any) => ({ isValid: !!data?.filePath, errors: data?.filePath ? [] : ['File Path required'] }),
      migrate: (_v, data) => data as any,
    });

    // 10. Delay / Timer Node (Utilities)
    this.plugins.set('delay_timer', {
      metadata: {
        id: 'delay_timer',
        name: 'Delay Timer',
        category: 'Utilities',
        description: 'Pause workflow execution for a specified duration',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['delay', 'sleep', 'wait', 'timer'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: false, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'durationSeconds', label: 'Duration (seconds)', type: 'text', required: true, defaultValue: '5' },
        ],
      },
      icon: 'Timer',
      color: '#64748B',
      defaultData: () => ({ durationSeconds: '5' }),
      validate: (data: any) => ({ isValid: !!data?.durationSeconds, errors: data?.durationSeconds ? [] : ['Duration required'] }),
      migrate: (_v, data) => data as any,
    });

    // 11. Custom Package Node (Installed Packages)
    this.plugins.set('custom_package_node', {
      metadata: {
        id: 'custom_package_node',
        name: 'Custom Package',
        category: 'Installed Packages',
        description: 'Execute logic from an installed community or custom package',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['package', 'plugin', 'custom', 'npm', 'module'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'packageName', label: 'Package Name', type: 'text', required: true, defaultValue: '@fluxa/pkg-example' },
        ],
      },
      icon: 'Package',
      color: '#8B5CF6',
      defaultData: () => ({ packageName: '@fluxa/pkg-example' }),
      validate: (data: any) => ({ isValid: !!data?.packageName, errors: data?.packageName ? [] : ['Package name required'] }),
      migrate: (_v, data) => data as any,
    });
  }
}
export const nodeRegistryInstance = new FetchNodeRegistry();

