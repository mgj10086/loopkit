/**
 * loopkit status — Show current LoopKit project status
 *
 * Displays:
 *   - Project config health
 *   - Registered loops and their LRS scores
 *   - Recent run history (from state directory)
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import { logger } from '../utils/logger.js';
import { validateCommand } from './validate.js';

export function statusCommand(targetDir: string = process.cwd()) {
  // Run validation to get current state
  const validation = validateCommand(targetDir);

  // Check state directory
  const stateDir = path.join(targetDir, '.loopkit', 'state');
  const hasStateDir = fs.existsSync(stateDir);

  // Check for run history
  let recentRuns: string[] = [];
  if (hasStateDir) {
    try {
      recentRuns = fs.readdirSync(stateDir)
        .filter(f => f.endsWith('.json'))
        .sort()
        .reverse()
        .slice(0, 5);
    } catch { /* ignore */ }
  }

  logger.section('LoopKit Status');

  if (validation.valid) {
    logger.kv('Configuration', '✅ Valid');
  } else {
    logger.kv('Configuration', '❌ Has errors');
    for (const err of validation.errors) {
      logger.warn(`  ${err}`);
    }
  }

  logger.kv('Project file', validation.projectFile || '(not found)');
  logger.kv('Loops', `${validation.loops.length} defined`);
  logger.kv('State directory', hasStateDir ? '✅ Present' : '⚠️  Not initialized');
  logger.sectionEnd();

  // Loop scores
  if (validation.loops.length > 0) {
    logger.section('Loop Scores');
    for (const loop of validation.loops) {
      if (loop.lrs) {
        const bar = getScoreBar(loop.lrs.total);
        logger.info(`  ${bar} ${loop.name} — ${loop.lrs.total}/100`);
      } else if (loop.errors.length > 0) {
        logger.error(`  ❌ ${loop.name} — ${loop.errors[0]}`);
      }
    }
    logger.sectionEnd();
  }

  // Recent runs
  if (recentRuns.length > 0) {
    logger.section('Recent Runs');
    for (const run of recentRuns) {
      logger.info(`  📋 ${run}`);
    }
    logger.sectionEnd();
  }

  // Next steps if not initialized
  if (!validation.projectFile) {
    logger.info('');
    logger.info('This directory is not a LoopKit project.');
    logger.info('Run "loopkit init" to get started.');
    logger.info('');
  }
}

function getScoreBar(score: number): string {
  const filled = Math.round(score / 10);
  const empty = 10 - filled;
  const blocks = '█'.repeat(filled) + '░'.repeat(empty);
  const color = score >= 80 ? '🟢' : score >= 60 ? '🟡' : '🔴';
  return `${color} ${blocks}`;
}
