/**
 * LoopKit — Loop Readiness Score (LRS)
 *
 * Evaluates a Loop configuration's production readiness on 7 dimensions.
 * Each dimension scored 0-100, with specific criteria and weights.
 * Total score is weighted average across all 7 dimensions.
 */

import type { LoopConfig } from '../schema/types.js';

export interface LRSScore {
  /** Overall score 0-100 */
  total: number;
  /** Per-dimension breakdown */
  dimensions: Record<string, number>;
  /** Specific flags that need attention */
  issues: string[];
  /** What's working well */
  strengths: string[];
}

const DIMENSIONS = [
  { key: 'quantifiable_goal', weight: 0.20, label: '目标可量化' },
  { key: 'termination_condition', weight: 0.20, label: '终止条件' },
  { key: 'verification', weight: 0.15, label: '验证机制' },
  { key: 'failure_recovery', weight: 0.15, label: '失败恢复' },
  { key: 'budget_control', weight: 0.10, label: '预算控制' },
  { key: 'human_intervention', weight: 0.10, label: '人工介入' },
  { key: 'state_persistence', weight: 0.10, label: '状态持久化' },
] as const;

export function calculateLRS(config: LoopConfig): LRSScore {
  const scores: Record<string, number> = {};
  const issues: string[] = [];
  const strengths: string[] = [];

  // 1. Quantifiable Goal
  if (config.description && config.description.length > 10) {
    scores.quantifiable_goal = config.name.length > 5 ? 80 : 60;
    strengths.push('有描述性的 loop 名称');
  } else {
    scores.quantifiable_goal = 30;
    issues.push('Loop 缺乏清晰描述，目标不可量化');
  }

  // 2. Termination Condition
  let termScore = 0;
  if (config.budget?.maxIterations) {
    termScore += 40;
    strengths.push(`设置了最大迭代次数 (${config.budget.maxIterations})`);
  }
  if (config.budget?.maxDurationMinutes) {
    termScore += 30;
    strengths.push(`设置了超时限制 (${config.budget.maxDurationMinutes}分钟)`);
  }
  if (config.budget?.maxTokens) {
    termScore += 30;
    strengths.push(`设置了 token 预算 (${config.budget.maxTokens})`);
  }
  scores.termination_condition = termScore;
  if (termScore < 40) {
    issues.push('缺少终止条件——Loop 可能无限运行');
  }

  // 3. Verification (Maker/Checker)
  if (config.verify) {
    const hasMaker = Array.isArray(config.verify.maker)
      ? config.verify.maker.length > 0
      : !!config.verify.maker;
    const hasChecker = Array.isArray(config.verify.checker)
      ? config.verify.checker.length > 0
      : !!config.verify.checker;

    if (hasMaker && hasChecker) {
      // Check if maker and checker are different
      const makers = Array.isArray(config.verify.maker) ? config.verify.maker : [config.verify.maker];
      const checkers = Array.isArray(config.verify.checker) ? config.verify.checker : [config.verify.checker];
      const isSeparated = !makers.some(m => checkers.includes(m));

      if (isSeparated) {
        scores.verification = 100;
        strengths.push('Maker ≠ Checker 分离，符合最佳实践');
      } else {
        scores.verification = 50;
        issues.push('Maker 和 Checker 使用同一 Agent —— Maker ≠ Checker 原则被违反');
      }
    } else {
      scores.verification = 40;
      issues.push('验证配置不完整，缺少 Maker 或 Checker');
    }
  } else {
    scores.verification = 20;
    issues.push('缺少验证机制 —— 建议添加 Maker/Checker 配置');
  }

  // 4. Failure Recovery
  if (config.verify?.autoRetry) {
    scores.failure_recovery = 70;
    strengths.push('启用了自动重试');
    if (config.verify.maxRounds && config.verify.maxRounds > 1) {
      scores.failure_recovery = 90;
      strengths.push(`设置了 ${config.verify.maxRounds} 轮验证重试`);
    }
  } else {
    scores.failure_recovery = 30;
    issues.push('未启用失败重试——Agent 报错后 Loop 可能静默失败');
  }

  // 5. Budget Control
  let budgetScore = 0;
  let budgetCount = 0;
  if (config.budget?.maxTokens) { budgetScore += 35; budgetCount++; }
  if (config.budget?.maxDurationMinutes) { budgetScore += 25; budgetCount++; }
  if (config.budget?.maxIterations) { budgetScore += 25; budgetCount++; }
  if (config.budget?.maxCostUsd) { budgetScore += 15; budgetCount++; }
  scores.budget_control = budgetCount >= 2 ? budgetScore : budgetScore - 20;
  if (budgetCount === 0) {
    issues.push('未设置任何预算控制——Agent 可能消耗大量资源');
  } else {
    strengths.push(`设置了 ${budgetCount} 项预算控制`);
  }

  // 6. Human Intervention
  if (config.verify?.maxRounds && config.verify.maxRounds >= 3) {
    scores.human_intervention = 80;
    strengths.push('验证失败后有人工介入机制');
  } else {
    scores.human_intervention = 50;
    // Not necessarily bad — L4/L5 loops minimize human intervention
  }

  // 7. State Persistence
  if (config.memory) {
    scores.state_persistence = config.memory.store === 'filesystem' ? 80 : 60;
    strengths.push(`启用了状态持久化 (${config.memory.store})`);
  } else {
    scores.state_persistence = 30;
    issues.push('缺少状态持久化——Loop 重启后会丢失上下文');
  }

  // Calculate weighted total
  let total = 0;
  for (const dim of DIMENSIONS) {
    const score = scores[dim.key] ?? 0;
    total += score * dim.weight;
  }

  return {
    total: Math.round(total),
    dimensions: scores,
    issues,
    strengths,
  };
}

export function scoreToGrade(score: number): string {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 65) return 'C';
  if (score >= 50) return 'D';
  return 'F';
}
