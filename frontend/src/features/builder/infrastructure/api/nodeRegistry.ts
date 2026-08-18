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
        supports_agent_tool: true,
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
            defaultValue: 'google/gemini-2.5-flash',
            options: [
              { label: 'Gemini 2.5 Flash', value: 'google/gemini-2.5-flash' },
              { label: 'Gemini 2.5 Pro', value: 'google/gemini-2.5-pro' },
              { label: 'GPT-4o', value: 'openai/gpt-4o' },
            ],
          },
          { name: 'prompt', label: 'System Instructions / Prompt', type: 'textarea', required: true, defaultValue: '' },
          {
            name: 'memoryProvider',
            label: 'Memory Provider',
            type: 'select',
            defaultValue: 'conversation',
            options: [
              { label: 'None', value: 'none' },
              { label: 'Conversation Memory', value: 'conversation' },
              { label: 'Workflow Memory', value: 'workflow' },
              { label: 'Persistent Memory', value: 'persistent' }
            ]
          },
          { name: 'memoryKey', label: 'Memory Key', type: 'text', defaultValue: 'customer_{{current_row.email}}' },
          { name: 'enabledTools', label: 'Enabled Tools (comma-separated)', type: 'text', defaultValue: 'google_sheets' },
          { name: 'apiKey', label: 'API Key / Token', type: 'secret', required: false, defaultValue: '' },
        ],
      },
      icon: 'Cpu',
      color: '#10B981',
      defaultData: () => ({
        model: 'google/gemini-2.5-flash',
        prompt: 'Summarize the input',
        memoryProvider: 'conversation',
        memoryKey: 'customer_{{current_row.email}}',
        enabledTools: 'google_sheets',
        apiKey: ''
      }),
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

    // 5b. Manual Execute Trigger Node (Triggers)
    this.plugins.set('manual_trigger', {
      metadata: {
        id: 'manual_trigger',
        name: 'On Execute Click',
        category: 'Triggers',
        description: 'Execute workflow when clicking the manual Run button',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['manual', 'click', 'run', 'execute', 'trigger'],
      },
      capabilities: { trigger: true, async: false, streaming: false, retryable: false, credentialRequired: false },
      schema: {
        version: 1,
        fields: [],
      },
      icon: 'Zap',
      color: '#10B981',
      defaultData: () => ({}),
      validate: () => ({ isValid: true, errors: [] }),
      migrate: (_v, data) => data as any,
    });

    // 5c. Telegram Trigger Node (Triggers)
    this.plugins.set('telegram_trigger', {
      metadata: {
        id: 'telegram_trigger',
        name: 'Telegram Trigger',
        category: 'Triggers',
        description: 'Trigger workflow when a message is received by your Telegram Bot',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['telegram', 'bot', 'chat', 'message'],
      },
      capabilities: { trigger: true, async: false, streaming: false, retryable: false, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'botToken', label: 'Telegram Bot Token ID (Vault)', type: 'secret', required: true, defaultValue: '' },
          { name: 'allowedChatId', label: 'Allowed Chat ID (Optional)', type: 'text', required: false, defaultValue: '' },
          { name: 'commandFilter', label: 'Command Filter (e.g. /run) (Optional)', type: 'text', required: false, defaultValue: '' }
        ],
      },
      icon: 'Send',
      color: '#10B981',
      defaultData: () => ({ botToken: '', allowedChatId: '', commandFilter: '' }),
      validate: (data: any) => ({ isValid: !!data?.botToken, errors: data?.botToken ? [] : ['Bot Token is required'] }),
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
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: true, supports_agent_tool: true },
      schema: {
        version: 1,
        fields: [
          { name: 'channel', label: 'Channel', type: 'text', required: true, defaultValue: '#general' },
          { name: 'message', label: 'Message Body', type: 'textarea', required: true, defaultValue: 'Hello from iNode!' },
        ],
      },
      icon: 'MessageSquare',
      color: '#EC4899',
      defaultData: () => ({ channel: '#general', message: 'Hello from iNode!' }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.channel) errors.push('Channel required');
        if (!data?.message) errors.push('Message required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });

    // 7. IF Condition Node (Logic)
    this.plugins.set('conditional', {
      metadata: {
        id: 'conditional',
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
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: false, supports_agent_tool: true },
      schema: {
        version: 1,
        fields: [
          { name: 'operation', label: 'Operation', type: 'select', defaultValue: 'read', options: [{ label: 'Read File', value: 'read' }, { label: 'Write File', value: 'write' }] },
          { name: 'filePath', label: 'File Path', type: 'text', required: true, defaultValue: '' },
        ],
      },
      icon: 'Folder',
      color: '#6366F1',
      defaultData: () => ({ operation: 'read', filePath: '' }),
      validate: (data: any) => ({ isValid: !!data?.filePath, errors: data?.filePath ? [] : ['File Path required'] }),
      migrate: (_v, data) => data as any,
    });

    // 9b. Google Sheets Node (Files)
    this.plugins.set('google_sheets', {
      metadata: {
        id: 'google_sheets',
        name: 'Google Sheets',
        category: 'Files',
        description: 'Read, write, append, or delete rows from Google Sheets',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['sheets', 'excel', 'table', 'row', 'google'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: false, supports_agent_tool: true },
      schema: {
        version: 1,
        fields: [
          {
            name: 'operation',
            label: 'Operation',
            type: 'select',
            defaultValue: 'read',
            options: [
              { label: 'Read Rows', value: 'read' },
              { label: 'Append Row', value: 'append' },
              { label: 'Update Row', value: 'update' },
              { label: 'Delete Row', value: 'delete' },
            ],
          },
          { name: 'spreadsheetId', label: 'Spreadsheet ID', type: 'text', required: true, defaultValue: 'default_sheet' },
          { name: 'range', label: 'Sheet Name / Range', type: 'text', defaultValue: 'Sheet1' },
          { name: 'rowId', label: 'Row ID (for Update/Delete)', type: 'text', defaultValue: '' },
          { name: 'row', label: 'Row Data (JSON, for Append)', type: 'textarea', defaultValue: '{}' },
          { name: 'updates', label: 'Updates Data (JSON, for Update)', type: 'textarea', defaultValue: '{}' },
        ],
      },
      icon: 'FileSpreadsheet',
      color: '#10B981',
      defaultData: () => ({ operation: 'read', spreadsheetId: 'default_sheet', range: 'Sheet1', rowId: '', row: '{}', updates: '{}' }),
      validate: (data: any) => ({ isValid: !!data?.spreadsheetId, errors: data?.spreadsheetId ? [] : ['Spreadsheet ID required'] }),
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
          { name: 'packageName', label: 'Package Name', type: 'text', required: true, defaultValue: '@fluxa/core-extensions' },
          { name: 'action', label: 'Action / Operation Name', type: 'text', required: true, defaultValue: 'execute' },
          { name: 'inputs_json', label: 'Inputs / Payload (JSON)', type: 'textarea', required: false, defaultValue: '{}' },
          { name: 'credentials_ref', label: 'API Credentials Reference ID', type: 'text', required: false, defaultValue: '' }
        ],
      },
      icon: 'Package',
      color: '#8B5CF6',
      defaultData: () => ({ 
        packageName: '@fluxa/core-extensions',
        action: 'execute',
        inputs_json: '{}',
        credentials_ref: ''
      }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.packageName) errors.push('Package name required');
        if (!data?.action) errors.push('Action name required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });
    // 12. Send Email Node (Communication)
    this.plugins.set('send_email', {
      metadata: {
        id: 'send_email',
        name: 'Send Email',
        category: 'Communication',
        description: 'Send custom proposals or outgoing messages via SMTP',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['email', 'smtp', 'mail', 'sendgrid', 'outbox'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: false, supports_agent_tool: true },
      schema: {
        version: 1,
        fields: [
          { name: 'smtp_host', label: 'SMTP Host', type: 'text', required: true, defaultValue: '' },
          { name: 'smtp_port', label: 'SMTP Port', type: 'text', required: true, defaultValue: '' },
          { name: 'username', label: 'Username', type: 'text', required: true, defaultValue: '' },
          { name: 'recipient', label: 'Recipient Email', type: 'text', required: true, defaultValue: '{{email}}' },
          { name: 'subject', label: 'Subject', type: 'text', required: true, defaultValue: 'Proposal' },
          { name: 'body', label: 'Email Body (Plain text or template)', type: 'textarea', required: true, defaultValue: '' },
          { name: 'password_ref', label: 'Vault SMTP Password Ref', type: 'secret', required: false, defaultValue: '' }
        ],
      },
      icon: 'Mail',
      color: '#F43F5E',
      defaultData: () => ({
        smtp_host: '',
        smtp_port: '',
        username: '',
        recipient: '{{email}}',
        subject: 'Proposal',
        body: 'Hello...',
        password_ref: ''
      }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.recipient) errors.push('Recipient Email is required');
        if (!data?.subject) errors.push('Subject is required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });
    // 13. Read Excel Node (Files)
    this.plugins.set('read_excel', {
      metadata: {
        id: 'read_excel',
        name: 'Read Excel / CSV',
        category: 'Files',
        description: 'Read rows of data from Excel or CSV files',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['excel', 'csv', 'table', 'rows', 'spreadsheet'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: false, supports_agent_tool: true },
      schema: {
        version: 1,
        fields: [
          { name: 'file_path', label: 'File Path (.csv, .xlsx)', type: 'text', required: true, defaultValue: '' },
          { name: 'output_var', label: 'Output Variable Name', type: 'text', required: true, defaultValue: 'rows' }
        ],
      },
      icon: 'FileSpreadsheet',
      color: '#10B981',
      defaultData: () => ({
        file_path: '',
        output_var: 'rows'
      }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.file_path) errors.push('File Path is required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });
    // 14. Loop Node (Logic)
    this.plugins.set('loop', {
      metadata: {
        id: 'loop',
        name: 'Loop / Iterator',
        category: 'Logic',
        description: 'Iterate over collection items (e.g. Excel rows) and run sub-nodes',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['loop', 'for', 'each', 'iterator', 'repeat'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: false, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'items_var', label: 'Items Variable (Array)', type: 'text', required: true, defaultValue: 'rows' },
          { name: 'loop_nodes_json', label: 'Loop Sub-Nodes Configurations (JSON)', type: 'textarea', defaultValue: '[]' }
        ],
      },
      icon: 'Repeat',
      color: '#F59E0B',
      defaultData: () => ({
        items_var: 'rows',
        loop_nodes_json: '[]'
      }),
      validate: (data: any) => {
        const errors: string[] = [];
        if (!data?.items_var) errors.push('Items Variable is required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });

    // 15. Telegram Send Message Node (Communication)
    this.plugins.set('telegram_send', {
      metadata: {
        id: 'telegram_send',
        name: 'Send Telegram Message',
        category: 'Communication',
        description: 'Send a message to a Telegram chat or group using a bot',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['telegram', 'bot', 'send', 'message'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'botToken', label: 'Telegram Bot Token ID (Vault)', type: 'secret', required: true, defaultValue: '' },
          { name: 'chatId', label: 'Chat ID', type: 'text', required: true, defaultValue: '{{telegram_chat_id}}' },
          { name: 'message', label: 'Message Text', type: 'textarea', required: true, defaultValue: 'Hello from iNode!' }
        ],
      },
      icon: 'Send',
      color: '#10B981',
      defaultData: () => ({ botToken: '', chatId: '{{telegram_chat_id}}', message: 'Hello from iNode!' }),
      validate: (data: any) => {
        const errors: string[] = [];
        const botToken = data?.botToken || data?.botToken_ref;
        if (!botToken) errors.push('Bot Token is required');
        const chatId = data?.chatId !== undefined && data?.chatId !== '' ? data.chatId : '{{telegram_chat_id}}';
        const message = data?.message !== undefined && data?.message !== '' ? data.message : 'Hello from iNode!';
        if (!chatId) errors.push('Chat ID is required');
        if (!message) errors.push('Message Text is required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });

    // 16. Read Email (IMAP) Node (Communication)
    this.plugins.set('read_email_imap', {
      metadata: {
        id: 'read_email_imap',
        name: 'Read Email Inbox (IMAP)',
        category: 'Communication',
        description: 'Connect to an IMAP server to read recent inbox messages',
        supportsVersion: 1,
        minimumEngineVersion: 1,
        aliases: ['email', 'imap', 'inbox', 'read', 'mail'],
      },
      capabilities: { trigger: false, async: true, streaming: false, retryable: true, credentialRequired: false },
      schema: {
        version: 1,
        fields: [
          { name: 'imapHost', label: 'IMAP Host', type: 'text', required: true, defaultValue: 'imap.gmail.com' },
          { name: 'imapPort', label: 'IMAP Port', type: 'text', required: true, defaultValue: '993' },
          { name: 'username', label: 'Username / Email Address', type: 'text', required: true, defaultValue: '' },
          { name: 'password_ref', label: 'Password ID (Vault)', type: 'secret', required: true, defaultValue: '' },
          { name: 'folder', label: 'Inbox Folder', type: 'text', required: true, defaultValue: 'INBOX' },
          { name: 'maxEmails', label: 'Max Emails to Fetch', type: 'text', required: true, defaultValue: '5' }
        ],
      },
      icon: 'Mail',
      color: '#F43F5E',
      defaultData: () => ({ imapHost: 'imap.gmail.com', imapPort: '993', username: '', password_ref: '', folder: 'INBOX', maxEmails: '5' }),
      validate: (data: any) => {
        const errors: string[] = [];
        const imapHost = data?.imapHost !== undefined && data?.imapHost !== '' ? data.imapHost : 'imap.gmail.com';
        if (!imapHost) errors.push('IMAP Host is required');
        if (!data?.username) errors.push('Username is required');
        const password = data?.password_ref || data?.password;
        if (!password) errors.push('Password credential is required');
        return { isValid: errors.length === 0, errors };
      },
      migrate: (_v, data) => data as any,
    });
  }
}
export const nodeRegistryInstance = new FetchNodeRegistry();

