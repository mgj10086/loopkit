/**
 * LoopCode — Core Type Definitions
 *
 * The six composable primitives of Loop Engineering:
 *   Trigger | Pipeline | Skill | Connector | SubAgent | Memory
 */

import { z } from 'zod';

// ── Trigger ──────────────────────────────────────────────────

export const TriggerType = z.enum(['webhook', 'cron', 'manual', 'event']);
export type TriggerType = z.infer<typeof TriggerType>;

export const WebhookEvent = z.enum([
  'pull_request',
  'push',
  'issues',
  'release',
  'workflow_dispatch',
]);
export type WebhookEvent = z.infer<typeof WebhookEvent>;

export const TriggerConfig = z.object({
  type: TriggerType,
  event: WebhookEvent.optional(),
  cron: z.string().optional(),
  /** Human-readable description of when this trigger fires */
  description: z.string().optional(),
});
export type TriggerConfig = z.infer<typeof TriggerConfig>;

// ── Agent / Skill References ─────────────────────────────────

export const AgentRef = z.object({
  /** The prompt the agent should follow */
  prompt: z.string().min(1),
  /** Optional skill reference (SKILL.md or npm package) */
  skill: z.string().optional(),
  /** Override model for this agent */
  model: z.string().optional(),
  /** Optional label for display/logging */
  label: z.string().optional(),
});
export type AgentRef = z.infer<typeof AgentRef>;

// ── Pipeline Steps ───────────────────────────────────────────

export const ParallelStep = z.object({
  parallel: z.array(AgentRef).min(1),
});
export type ParallelStep = z.infer<typeof ParallelStep>;

export const SequentialStep = z.object({
  agents: z.array(AgentRef).min(1),
});
export type SequentialStep = z.infer<typeof SequentialStep>;

export const PipelineStep = z.union([AgentRef, ParallelStep, SequentialStep]);
export type PipelineStep = z.infer<typeof PipelineStep>;

// ── Verification (Maker/Checker) ──────────────────────────────

export const VerifyConfig = z.object({
  /** The agent(s) that PRODUCE output */
  maker: z.union([z.string(), z.array(z.string())]),
  /** The agent(s) that VERIFY/CHALLENGE the output */
  checker: z.union([z.string(), z.array(z.string())]),
  /** Max verification rounds before human escalation */
  maxRounds: z.number().int().min(1).max(10).default(3),
  /** Whether verification failures should be auto-retried */
  autoRetry: z.boolean().default(true),
});
export type VerifyConfig = z.infer<typeof VerifyConfig>;

// ── Budget ───────────────────────────────────────────────────

export const BudgetConfig = z.object({
  /** Max tokens this loop can consume */
  maxTokens: z.number().int().positive().optional(),
  /** Max execution time in minutes */
  maxDurationMinutes: z.number().int().positive().optional(),
  /** Max number of iterations */
  maxIterations: z.number().int().positive().optional(),
  /** Max cost in USD (approximate) */
  maxCostUsd: z.number().positive().optional(),
});
export type BudgetConfig = z.infer<typeof BudgetConfig>;

// ── Memory ───────────────────────────────────────────────────

export const MemoryStore = z.enum(['filesystem', 'memory', 'claude']);
export type MemoryStore = z.infer<typeof MemoryStore>;

export const MemoryConfig = z.object({
  /** Where to persist state */
  store: MemoryStore.default('filesystem'),
  /** Path relative to project root */
  path: z.string().default('.loopcode/state'),
  /** Whether to persist full context or just summaries */
  persistence: z.enum(['full', 'summary', 'minimal']).default('full'),
});
export type MemoryConfig = z.infer<typeof MemoryConfig>;

// ── Complete Loop Config ─────────────────────────────────────

export const LoopConfig = z.object({
  /** Name of this loop (used for CLI commands and logging) */
  name: z.string().min(1),
  /** Human-readable description */
  description: z.string().optional(),
  /** The trigger that starts this loop */
  trigger: TriggerConfig,
  /** The main execution pipeline */
  pipeline: z.array(PipelineStep).min(1),
  /** Optional verification step (Maker/Checker) */
  verify: VerifyConfig.optional(),
  /** Resource budget controls */
  budget: BudgetConfig.optional(),
  /** State persistence configuration */
  memory: MemoryConfig.optional(),
  /** Tags for discoverability */
  tags: z.array(z.string()).optional(),
});
export type LoopConfig = z.infer<typeof LoopConfig>;

// ── Project Config (loopcode.yaml) ────────────────────────────

export const ProjectConfig = z.object({
  /** Schema version */
  version: z.literal('1').default('1'),
  /** Project-level settings */
  settings: z.object({
    /** Default budget applied to all loops */
    defaultBudget: BudgetConfig.optional(),
    /** Default memory config applied to all loops */
    defaultMemory: MemoryConfig.optional(),
    /** Whether to enforce Maker/Checker by default */
    enforceMakerChecker: z.boolean().default(true),
  }).optional(),
  /** The loops defined in this project */
  loops: z.record(z.string(), LoopConfig),
});
export type ProjectConfig = z.infer<typeof ProjectConfig>;
