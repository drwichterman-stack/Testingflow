/**
 * The subset of expo-sqlite's SQLiteDatabase that the app uses. Tests pass
 * an adapter over Node's built-in SQLite with the same shape, so the real
 * schema and queries are exercised in Jest.
 */
export type BindValue = string | number | null;

export interface Db {
  execAsync(source: string): Promise<void>;
  runAsync(source: string, params: BindValue[]): Promise<{ changes: number }>;
  getAllAsync<T>(source: string, params: BindValue[]): Promise<T[]>;
  getFirstAsync<T>(source: string, params: BindValue[]): Promise<T | null>;
  withTransactionAsync(task: () => Promise<void>): Promise<void>;
}
