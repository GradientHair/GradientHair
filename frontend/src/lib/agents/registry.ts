import type { AgentDefinition, AgentRegistry } from "./types";

const agents = new Map<string, AgentDefinition>();

const defaults: AgentDefinition[] = [
  {
    id: "moderator",
    name: "Moderator",
    role: "moderator",
    description: "Keeps the discussion on-topic and balances participation.",
    capabilities: ["topic-drift", "participation-balance", "gentle-interrupt"],
  },
  {
    id: "scribe",
    name: "Scribe",
    role: "scribe",
    description: "Captures transcript highlights and action items.",
    capabilities: ["transcript", "summaries", "action-items"],
  },
];

defaults.forEach((agent) => agents.set(agent.id, agent));

export const registry: AgentRegistry = {
  list: () => Array.from(agents.values()),
  get: (id) => agents.get(id),
  register: (agent) => agents.set(agent.id, agent),
};
