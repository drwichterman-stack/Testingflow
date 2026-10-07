/**
 * A Db backed by Node's built-in SQLite, so tests run the app's real schema
 * and SQL. (expo-sqlite itself needs a device or simulator.)
 */
import { randomUUID } from 'crypto';
import type { BindValue, Db } from '../../src/db/types';

type Stmt = { run(...p: BindValue[]): { changes: number | bigint }; all(...p: BindValue[]): unknown[]; get(...p: BindValue[]): unknown };
type SyncDb = { exec(sql: string): void; prepare(sql: string): Stmt; close(): void };

export function createTestDb(): Db & { close(): void } {
  const { DatabaseSync } = (process as any).getBuiltinModule('node:sqlite') as { DatabaseSync: new (p: string) => SyncDb };
  const d = new DatabaseSync(':memory:');
  return {
    async execAsync(sql) { d.exec(sql); },
    async runAsync(sql, params) { return { changes: Number(d.prepare(sql).run(...params).changes) }; },
    async getAllAsync<T>(sql: string, params: BindValue[]) { return d.prepare(sql).all(...params) as T[]; },
    async getFirstAsync<T>(sql: string, params: BindValue[]) { return (d.prepare(sql).get(...params) ?? null) as T | null; },
    async withTransactionAsync(task) {
      d.exec('BEGIN');
      try { await task(); d.exec('COMMIT'); } catch (e) { d.exec('ROLLBACK'); throw e; }
    },
    close() { d.close(); },
  };
}

export const newId = () => randomUUID();
