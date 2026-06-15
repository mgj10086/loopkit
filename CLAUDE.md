# CLAUDE.md — LoopKit

LoopKit is the open-source standard for autonomous AI agent loops.

## Project Overview

A CLI + runtime for composing, verifying, and deploying AI agent loops using six primitives:
**Trigger | Pipeline | Skill | Connector | SubAgent | Memory**.

Core philosophy: **Maker ≠ Checker** — the agent that produces output must never be
the same agent that verifies it.

## Commands

```bash
npm run dev -- init              # Init project
npm run dev -- validate          # Validate + LRS scoring
npm run dev -- run pr-review     # Run a loop
npm run dev -- status            # Show status
```

## Architecture

```
src/
├── cli.ts                       # CLI entry point (Commander)
├── commands/
│   ├── init.ts                  # loopkit init
│   ├── validate.ts              # loopkit validate (inc. LRS)
│   ├── run.ts                   # loopkit run <name>
│   └── status.ts                # loopkit status
├── schema/
│   └── types.ts                 # Zod schemas for all config types
├── engine/                      # (W2+) Runtime engine
└── utils/
    ├── lrs.ts                   # Loop Readiness Score calculator
    └── logger.ts                # CLI logger

loops/                           # Built-in loop templates
├── pr-review.yaml               # PR review loop
└── daily-triage.yaml            # Issue triage loop
```

## Key Design Rules

1. **Maker ≠ Checker** — Enforced at the schema type level. VerifyConfig requires
   separate maker and checker agent references.
2. **Explicit termination** — Every loop must define at least one termination
   condition (iterations, duration, or tokens). LRS fails otherwise.
3. **State persistence** — Every loop should define a memory store. Stateless loops
   lose context on restart.
4. **Declarative config** — Loop behavior is defined in YAML, not code. The CLI
   interprets, the YAML is the source of truth.
5. **Composability** — Loops can reference other loops as sub-steps (W3+).

## Loop Readiness Score (LRS)

Seven dimensions, 0-100 weighted:
- 目标可量化 (20%) | 终止条件 (20%) | 验证机制 (15%)
- 失败恢复 (15%) | 预算控制 (10%) | 人工介入 (10%) | 状态持久化 (10%)

Grade A ≥ 90, B ≥ 80, C ≥ 65, D ≥ 50, F < 50.

## Current Status

MVP Phase (Week 1): Schema + CLI + LRS. Engine runtime is scaffolded but does not
yet make actual LLM calls — those will be delegated to MCP/Agent tools in W2.

## Links

- [GitHub](https://github.com/mgj/loopkit)
- [Docs](https://github.com/mgj/loopkit#readme)
