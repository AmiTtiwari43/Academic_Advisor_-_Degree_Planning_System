import { apiClient } from './client';

export interface AssistantCitation {
  source_type: string;
  reference: string;
  details: string;
}

export interface AssistantQueryPayload {
  prompt: string;
  student_record_id?: string;
}

export interface AssistantResponse {
  answer: string;
  citations: AssistantCitation[];
  grounded_context_summary: string;
  disclaimer: string;
}

export interface AssistantCapabilities {
  supported_query_types: string[];
  disclaimer: string;
  grounding_sources: string[];
  rate_limit: string;
}

export const assistantApi = {
  query: (payload: AssistantQueryPayload): Promise<AssistantResponse> => {
    return apiClient.post<AssistantResponse>('/api/v1/assistant/query/', payload);
  },

  getCapabilities: (): Promise<AssistantCapabilities> => {
    return apiClient.get<AssistantCapabilities>('/api/v1/assistant/capabilities/');
  },
};
