/**
 * App-wide state (Context API): the database, the local user id, and a
 * version counter that screens watch to reload after any write.
 * Also records study time: one session per stretch of time the app is in
 * the foreground, saved every 30 seconds and when the app goes to the
 * background.
 */
import { useFocusEffect } from '@react-navigation/native';
import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, AppState, StyleSheet, Text, View } from 'react-native';
import * as repo from '../db/repo';
import type { Db } from '../db/types';
import { colors } from '../theme';
import type { Course } from '../types';

interface AppData {
  db: Db;
  userId: string;
  version: number;
  refresh: () => void;
  newId: () => string;
  restartStudySession: () => Promise<void>;
}

const Ctx = createContext<AppData | null>(null);

export const STUDY_TICK_MS = 30_000;

export function AppDataProvider({ db, newId, children, trackStudyTime = true }:
  { db: Db; newId: () => string; children: ReactNode; trackStudyTime?: boolean }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const session = useRef<string | null>(null);

  useEffect(() => {
    repo.initDatabase(db, newId).then(setUserId, (e) => setError(String(e)));
  }, [db, newId]);

  const startSession = useCallback(async () => {
    if (!userId || !trackStudyTime) return;
    const id = newId();
    session.current = id;
    await repo.startStudySession(db, userId, id, new Date());
  }, [db, newId, userId, trackStudyTime]);

  const touchSession = useCallback(async () => {
    if (session.current) await repo.touchStudySession(db, session.current, new Date());
  }, [db]);

  useEffect(() => {
    if (!userId || !trackStudyTime) return;
    startSession();
    const timer = setInterval(touchSession, STUDY_TICK_MS);
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        if (!session.current) startSession();
      } else if (session.current) {
        touchSession();
        session.current = null;
      }
    });
    return () => {
      clearInterval(timer);
      sub.remove();
      touchSession();
      session.current = null;
    };
  }, [userId, trackStudyTime, startSession, touchSession]);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const restartStudySession = useCallback(async () => {
    session.current = null;
    await startSession();
  }, [startSession]);

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.err}>The study database could not be opened.</Text>
        <Text style={styles.detail}>{error}</Text>
      </View>
    );
  }
  if (!userId) {
    return <View style={styles.center}><ActivityIndicator color={colors.primary} /></View>;
  }
  return (
    <Ctx.Provider value={{ db, userId, version, refresh, newId, restartStudySession }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAppData(): AppData {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAppData must be used inside AppDataProvider');
  return v;
}

/**
 * Load data when the screen gains focus and after any write elsewhere.
 * `key` reloads the data when it changes (for example the unit being shown).
 */
export function useLoader<T>(load: (d: AppData) => Promise<T>, key?: unknown): T | null {
  const app = useAppData();
  const [value, setValue] = useState<T | null>(null);
  useFocusEffect(useCallback(() => {
    let live = true;
    load(app).then((v) => { if (live) setValue(v); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.version, app.userId, key]));
  return value;
}

export function useCourses(): Course[] | null {
  return useLoader((a) => repo.loadCourses(a.db, a.userId));
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, backgroundColor: colors.bg },
  err: { fontSize: 16, fontWeight: '600', color: colors.error, marginBottom: 8, textAlign: 'center' },
  detail: { fontSize: 13, color: colors.muted, textAlign: 'center' },
});
