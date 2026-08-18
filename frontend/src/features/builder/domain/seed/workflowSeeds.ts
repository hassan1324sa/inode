import type { WorkflowNode, WorkflowEdge, WorkflowMetadata } from '../../domain/models/workflow';

export const DEMO_WORKFLOW_ID = 'wf_enterprise_lead_triage';

export interface WorkflowSeedData {
  metadata: WorkflowMetadata;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables: Record<string, unknown>;
}

export const DEMO_WORKFLOW_SEED: WorkflowSeedData = {
  metadata: {
    id: DEMO_WORKFLOW_ID,
    name: 'Enterprise AI Lead Triage & VIP Outreach',
    description: 'Real-time lead ingestion via Webhook, Clearbit data enrichment, conditional VIP scoring, AI executive proposal drafting, and Slack sales notifications.',
    tags: ['AI', 'Enterprise', 'Lead Scoring', 'Automation'],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  nodes: [
    {
      id: 'node-webhook',
      type: 'webhook_trigger',
      version: 1,
      position: { x: 50, y: 220 },
      data: {
        path: '/api/v1/webhook/leads',
        method: 'POST',
        label: '1. Inbound Lead Webhook',
      },
    },
    {
      id: 'node-transform',
      type: 'transform_json',
      version: 1,
      position: { x: 380, y: 220 },
      data: {
        query: '.payload | {email: .email, company: .company_name, source: .utm_source}',
        label: '2. Extract Lead Profile',
      },
    },
    {
      id: 'node-http',
      type: 'http_request',
      version: 1,
      position: { x: 710, y: 220 },
      data: {
        method: 'POST',
        url: 'https://api.clearbit.com/v2/companies/find',
        headers: '{"Authorization": "Bearer YOUR_API_TOKEN"}',
        body: '{"domain": "{{company}}"}',
        label: '3. Clearbit Enrichment API',
      },
    },
    {
      id: 'node-if',
      type: 'if_condition',
      version: 1,
      position: { x: 1040, y: 220 },
      data: {
        expression: 'lead_score >= 80 and employees > 100',
        label: '4. Is Enterprise VIP Lead?',
      },
    },
    {
      id: 'node-ai',
      type: 'ai_agent',
      version: 1,
      position: { x: 1370, y: 60 },
      data: {
        model: 'gemini-1.5-pro',
        prompt: 'Draft a tailored VIP executive proposal for {{email}} using enriched CRM & Clearbit company insights.',
        credentialId: 'SELECT_CREDENTIAL',
        label: '5. AI VIP Pitch Draft',
      },
    },
    {
      id: 'node-slack',
      type: 'slack_notification',
      version: 1,
      position: { x: 1370, y: 380 },
      data: {
        channel: '#enterprise-sales-alerts',
        message: '🚨 VIP Enterprise Lead Detected: {{email}} (Company: {{company}} | Score: {{lead_score}})',
        label: '6. Notify Sales Team',
      },
    },
    {
      id: 'node-storage',
      type: 'file_storage',
      version: 1,
      position: { x: 1720, y: 220 },
      data: {
        operation: 'write',
        filePath: '',
        label: '7. Archive VIP Lead Record',
      },
    },
  ],
  edges: [
    {
      id: 'e-webhook-transform',
      source: 'node-webhook',
      target: 'node-transform',
      label: 'Raw JSON Payload',
    },
    {
      id: 'e-transform-http',
      source: 'node-transform',
      target: 'node-http',
      label: 'Lead Email & Domain',
    },
    {
      id: 'e-http-if',
      source: 'node-http',
      target: 'node-if',
      label: 'Enriched Company Data',
    },
    {
      id: 'e-if-ai',
      source: 'node-if',
      target: 'node-ai',
      sourceHandle: 'true',
      label: 'VIP (Score >= 80)',
    },
    {
      id: 'e-if-slack',
      source: 'node-if',
      target: 'node-slack',
      sourceHandle: 'false',
      label: 'Standard Lead',
    },
    {
      id: 'e-ai-storage',
      source: 'node-ai',
      target: 'node-storage',
      label: 'Generated Pitch Proposal',
    },
    {
      id: 'e-slack-storage',
      source: 'node-slack',
      target: 'node-storage',
      label: 'Alert Log',
    },
  ],
  variables: {
    lead_score: 85,
    employees: 450,
  },
};

export function getCleanInitialWorkflowState(id: string): WorkflowSeedData {
  if (id === DEMO_WORKFLOW_ID) {
    return DEMO_WORKFLOW_SEED;
  }
  return {
    metadata: {
      id,
      name: 'Untitled Workflow',
      description: '',
      tags: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
    nodes: [],
    edges: [],
    variables: {},
  };
}
