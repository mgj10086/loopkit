/**
 * loopcode validate — Validate LoopCode configuration
 *
 * Parses loopcode.yaml and all loop files, checks schema compliance,
 * calculates Loop Readiness Score for each loop.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import * as yaml from 'js-yaml';
import { ProjectConfig, LoopConfig } from '../schema/types.js';
import { calculateLRS, scoreToGrade } from '../utils/lrs.js';
import { logger } from '../utils/logger.js';

export interface ValidationResult {
  valid: boolean;
  projectFile: string;
  loops: Array<{
    name: string;
    valid: boolean;
    errors: string[];
    lrs: ReturnType<typeof calculateLRS> | null;
  }>;
  errors: string[];
}

export function validateCommand(targetDir: string = process.cwd()): ValidationResult {
  const result: ValidationResult = {
    valid: true,
    projectFile: '',
    loops: [],
    errors: [],
  };

  // 1. Find and parse project config
  const projectFile = findProjectFile(targetDir);
  if (!projectFile) {
    result.valid = false;
    result.errors.push('No loopcode.yaml or loopcode.yml found in this directory or parents.');
    return result;
  }
  result.projectFile = projectFile;

  let projectConfig: ProjectConfig;
  try {
    const content = fs.readFileSync(projectFile, 'utf-8');
    const parsed = yaml.load(content);
    projectConfig = ProjectConfig.parse(parsed);
  } catch (err) {
    result.valid = false;
    const msg = err instanceof Error ? err.message : String(err);
    result.errors.push(`Failed to parse ${path.basename(projectFile)}: ${msg}`);
    return result;
  }

  logger.section('Project Config');
  logger.kv('File', path.relative(targetDir, projectFile));
  logger.kv('Loops defined', String(Object.keys(projectConfig.loops).length));
  logger.sectionEnd();

  // 2. Discover and validate individual loop files
  const loopsDir = path.join(targetDir, 'loops');
  if (fs.existsSync(loopsDir)) {
    const files = fs.readdirSync(loopsDir).filter(f => f.endsWith('.yaml') || f.endsWith('.yml'));
    for (const file of files) {
      const loopPath = path.join(loopsDir, file);
      try {
        const content = fs.readFileSync(loopPath, 'utf-8');
        const parsed = yaml.load(content);
        const loopConfig = LoopConfig.parse(parsed);

        // Calculate LRS
        const lrs = calculateLRS(loopConfig);

        result.loops.push({
          name: loopConfig.name || file,
          valid: true,
          errors: [],
          lrs,
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        result.loops.push({
          name: file,
          valid: false,
          errors: [msg],
          lrs: null,
        });
        result.valid = false;
      }
    }
  }

  // 3. Validate project-level loop configs
  for (const [name, config] of Object.entries(projectConfig.loops)) {
    try {
      LoopConfig.parse(config);
      const lrs = calculateLRS(config);
      result.loops.push({ name, valid: true, errors: [], lrs });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      result.loops.push({ name, valid: false, errors: [msg], lrs: null });
      result.valid = false;
    }
  }

  // 4. Print summary
  printSummary(result);

  return result;
}

function printSummary(result: ValidationResult) {
  const total = result.loops.length;
  const valid = result.loops.filter(l => l.valid).length;
  const failed = result.loops.filter(l => !l.valid).length;

  logger.section('Validation Summary');
  logger.kv('Total Loops', String(total));
  logger.kv('Valid', `${valid} ✅`);
  if (failed > 0) logger.kv('Failed', `${failed} ❌`);
  logger.sectionEnd();

  for (const loop of result.loops) {
    if (loop.lrs) {
      const grade = scoreToGrade(loop.lrs.total);
      logger.info(`\n${loop.name} — LRS: ${loop.lrs.total}/100 (Grade ${grade})`);

      if (loop.lrs.strengths.length > 0) {
        for (const s of loop.lrs.strengths) {
          logger.info(`  ✅ ${s}`);
        }
      }
      if (loop.lrs.issues.length > 0) {
        for (const issue of loop.lrs.issues) {
          logger.warn(`  ⚠️  ${issue}`);
        }
      }
    }
    if (loop.errors.length > 0) {
      for (const err of loop.errors) {
        logger.error(`  ❌ ${err}`);
      }
    }
  }
}

function findProjectFile(dir: string): string | null {
  const candidates = ['loopcode.yaml', 'loopcode.yml'];
  for (const name of candidates) {
    const p = path.join(dir, name);
    if (fs.existsSync(p)) return p;
  }

  // Check parent (one level up)
  const parent = path.resolve(dir, '..');
  if (parent !== dir) {
    return findProjectFile(parent);
  }

  return null;
}
