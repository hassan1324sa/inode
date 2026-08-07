import type { PluginId, Version } from '../models/workflow';


export type FieldType = 'text' | 'textarea' | 'select' | 'switch' | 'secret' | 'code';

export interface NodeFieldSchema {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  defaultValue?: unknown;
  description?: string;
  options?: { label: string; value: string }[]; // For select type
}

export interface NodeSchema {
  version: number;
  fields: NodeFieldSchema[];
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface NodePlugin {
  metadata: {
    id: PluginId;
    name: string;
    category: string;
    description?: string;
    supportsVersion: Version;
    minimumEngineVersion: Version;
    deprecated?: boolean;
    experimental?: boolean;
    aliases?: string[];
  };

  capabilities: {
    trigger: boolean;
    async: boolean;
    streaming: boolean;
    retryable: boolean;
    credentialRequired: boolean;
    supports_agent_tool?: boolean;
  };

  schema: NodeSchema;
  icon: string;
  color: string;

  defaultData(): Record<string, unknown>;
  validate(data: unknown): ValidationResult;
  migrate(fromVersion: number, data: unknown): Record<string, unknown>;
}
