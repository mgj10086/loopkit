/**
 * loopkit init — Initialize a new LoopKit project
 *
 * Scaffolds the project structure with loopkit.yaml and default loop templates.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import { logger } from '../utils/logger.js';

const DEFAULT_PROJECT_YAML = `# LoopKit Project Configuration
# See https://github.com/mgj/loopkit for documentation
version: "1"

settings:
  defaultBudget:
    maxTokens: 500000
    maxDurationMinutes: 30
    maxIterations: 10
  defaultMemory:
    store: filesystem
    path: .loopkit/state
  enforceMakerChecker: true

loops: {}
`;

const PR_REVIEW_LOOP_YAML = `# Pull Request Review Loop
# Automatically reviews PRs with Maker/Checker separation
name: pr-review
description: >
  Automatically reviews pull requests for bugs, security issues,
  and code quality. Uses separate agents for review and verification.

trigger:
  type: webhook
  event: pull_request

pipeline:
  - parallel:
      - prompt: "Review this PR for correctness bugs. Focus on logic errors, edge cases, and race conditions."
        label: Bug Review
      - prompt: "Review this PR for security vulnerabilities. Focus on injection, auth, and data exposure."
        label: Security Review
      - prompt: "Review this PR for code quality and maintainability."
        label: Quality Review
      - prompt: "Review this PR for performance issues."
        label: Performance Review

verify:
  maker: [Bug Review, Security Review, Quality Review, Performance Review]
  checker: "Adversarial Verifier"
  maxRounds: 3
  autoRetry: true

budget:
  maxTokens: 500000
  maxDurationMinutes: 30

memory:
  store: filesystem
  path: .loopkit/state

tags: [code-review, pr, automation]
`;

const DAILY_TRIAGE_YAML = `# Daily Issue Triage Loop
# Scans and categorizes new issues daily
name: daily-triage
description: Automatically categorizes and prioritizes new GitHub issues.

trigger:
  type: cron
  cron: "0 9 * * 1-5"

pipeline:
  - prompt: >
      Scan all open issues without labels.
      For each issue:
      1. Categorize it (bug/feature/question/docs)
      2. Assess priority (critical/high/medium/low)
      3. Suggest appropriate labels
      4. Assign to the most relevant team member
    label: Issue Triage

verify:
  maker: Issue Triage
  checker: Triage Verifier
  maxRounds: 2
  autoRetry: true

budget:
  maxTokens: 200000
  maxDurationMinutes: 15
  maxIterations: 1

memory:
  store: filesystem
  path: .loopkit/state

tags: [issues, triage, automation]
`;

export async function initCommand(targetDir: string = process.cwd(), options: { force?: boolean } = {}) {
  const projectFile = path.join(targetDir, 'loopkit.yaml');
  const loopsDir = path.join(targetDir, 'loops');

  // Check if already initialized
  if (fs.existsSync(projectFile) && !options.force) {
    logger.warn('LoopKit already initialized in this directory.');
    logger.info(`  File: ${projectFile}`);
    logger.info('  Use --force to overwrite.');
    return;
  }

  // Create project file
  fs.writeFileSync(projectFile, DEFAULT_PROJECT_YAML, 'utf-8');
  logger.info(`Created ${path.relative(targetDir, projectFile)}`);

  // Create loops directory
  if (!fs.existsSync(loopsDir)) {
    fs.mkdirSync(loopsDir, { recursive: true });
  }

  // Write default loops
  const prReviewPath = path.join(loopsDir, 'pr-review.yaml');
  if (!fs.existsSync(prReviewPath) || options.force) {
    fs.writeFileSync(prReviewPath, PR_REVIEW_LOOP_YAML, 'utf-8');
    logger.info(`Created ${path.relative(targetDir, prReviewPath)}`);
  }

  const triagePath = path.join(loopsDir, 'daily-triage.yaml');
  if (!fs.existsSync(triagePath) || options.force) {
    fs.writeFileSync(triagePath, DAILY_TRIAGE_YAML, 'utf-8');
    logger.info(`Created ${path.relative(targetDir, triagePath)}`);
  }

  // Create state directory
  const stateDir = path.join(targetDir, '.loopkit', 'state');
  if (!fs.existsSync(stateDir)) {
    fs.mkdirSync(stateDir, { recursive: true });
  }

  logger.section('LoopKit Ready');
  logger.kv('Config', 'loopkit.yaml');
  logger.kv('Loops', `${loopsDir}/ (2 templates)`);
  logger.kv('State', '.loopkit/state/');
  logger.sectionEnd();

  logger.info('');
  logger.info('Next steps:');
  logger.info('  1. Edit loopkit.yaml to configure your loops');
  logger.info('  2. Run "loopkit validate" to check your config');
  logger.info('  3. Run "loopkit run pr-review" to test a loop');
  logger.info('');
}
