export type AgentRole = "moderator" | "scribe" | "coach" | "custom";

export type AgentDefinition = {
  id: string;
  name: string;
  role: AgentRole;
  description: string;
  capabilities: string[];
  systemPrompt?: string;
};

export type AgentRegistry = {
  list: () => AgentDefinition[];
  get: (id: string) => AgentDefinition | undefined;
  register: (agent: AgentDefinition) => void;
};
