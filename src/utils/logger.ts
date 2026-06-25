/**
 * LoopCode — Simple logger utility
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

const PREFIX = {
  [LogLevel.DEBUG]: '🔍',
  [LogLevel.INFO]: 'ℹ️',
  [LogLevel.WARN]: '⚠️',
  [LogLevel.ERROR]: '❌',
};

class Logger {
  private level: LogLevel = LogLevel.INFO;

  setLevel(level: LogLevel) {
    this.level = level;
  }

  debug(...args: unknown[]) {
    if (this.level <= LogLevel.DEBUG) console.log(PREFIX[LogLevel.DEBUG], ...args);
  }

  info(...args: unknown[]) {
    if (this.level <= LogLevel.INFO) console.log(PREFIX[LogLevel.INFO], ...args);
  }

  warn(...args: unknown[]) {
    if (this.level <= LogLevel.WARN) console.warn(PREFIX[LogLevel.WARN], ...args);
  }

  error(...args: unknown[]) {
    if (this.level <= LogLevel.ERROR) console.error(PREFIX[LogLevel.ERROR], ...args);
  }

  /** Print a section header */
  section(title: string) {
    console.log(`\n┌─ ${title} ${'─'.repeat(Math.max(0, 60 - title.length))}`);
  }

  /** Print a key-value pair */
  kv(key: string, value: string) {
    console.log(`│ ${key}: ${value}`);
  }

  /** Close a section */
  sectionEnd() {
    console.log(`└${'─'.repeat(62)}`);
  }
}

export const logger = new Logger();
