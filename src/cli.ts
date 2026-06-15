#!/usr/bin/env node

/**
 * LoopKit CLI — The open-source standard for autonomous AI agent loops.
 *
 * Usage:
 *   loopkit init                  Initialize a new LoopKit project
 *   loopkit validate              Validate loop configuration
 *   loopkit run <loop-name>       Execute a loop
 *   loopkit status                Show project status
 *   loopkit --help                Show help
 *   loopkit --version             Show version
 */

import { Command } from 'commander';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { initCommand } from './commands/init.js';
import { validateCommand } from './commands/validate.js';
import { runCommand } from './commands/run.js';
import { statusCommand } from './commands/status.js';

const require = createRequire(import.meta.url);
const pkg = require('../package.json');

const program = new Command();

program
  .name('loopkit')
  .description('The open-source standard for autonomous AI agent loops')
  .version(pkg.version);

program
  .command('init')
  .description('Initialize a new LoopKit project in the current directory')
  .option('-f, --force', 'Overwrite existing files')
  .action(async (options) => {
    await initCommand(process.cwd(), options);
  });

program
  .command('validate')
  .description('Validate loop configuration and calculate readiness scores')
  .action(() => {
    const result = validateCommand(process.cwd());
    process.exit(result.valid ? 0 : 1);
  });

program
  .command('run')
  .description('Execute a named loop')
  .argument('<loop-name>', 'Name of the loop to run')
  .action(async (loopName: string) => {
    const result = await runCommand(loopName, process.cwd());
    process.exit(result.success ? 0 : 1);
  });

program
  .command('status')
  .description('Show project status and loop readiness scores')
  .action(() => {
    statusCommand(process.cwd());
  });

program.parse(process.argv);
