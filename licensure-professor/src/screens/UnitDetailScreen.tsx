import Ionicons from '@expo/vector-icons/Ionicons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useEffect } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ProgressBar } from '../components/ProgressBar';
import * as repo from '../db/repo';
import type { HomeStackParams } from '../navigation/types';
import { useAppData, useCourses, useLoader } from '../state/AppData';
import { colors, common, space } from '../theme';

type Props = NativeStackScreenProps<HomeStackParams, 'UnitDetail'>;

export function UnitDetailScreen({ navigation, route }: Props) {
  const app = useAppData();
  const courses = useCourses();
  const stats = useLoader((a) => repo.quizStats(a.db, a.userId));
  const unit = courses?.find((c) => c.id === route.params.unitId);

  useEffect(() => {
    if (unit) {
      navigation.setOptions({ title: unit.title.split(':')[0] });
      repo.touchCourse(app.db, app.userId, unit.id);
    }
  }, [unit?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!unit) return <View style={common.screen} />;
  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <Text style={common.h1}>{unit.title}</Text>
      <Text style={[common.muted, styles.desc]}>{unit.description}</Text>
      <View style={styles.progressRow}>
        <Text style={styles.percent}>{unit.progressPercentage}%</Text>
        <Text style={common.muted}>unit progress</Text>
      </View>
      <ProgressBar percent={unit.progressPercentage} height={8} />

      <Text style={common.h2} accessibilityRole="header">Lessons</Text>
      <View style={styles.list}>
        {unit.lessons.map((l) => (
          <Pressable key={l.id} testID={`lesson-${l.order}`} accessibilityRole="button"
                     onPress={() => navigation.navigate('LessonViewer', { unitId: unit.id, lessonId: l.id })}
                     style={({ pressed }) => [common.card, styles.row, pressed && styles.pressed]}>
            <View style={styles.rowText}>
              <Text style={common.title}>{l.order}. {l.title}</Text>
              <Text style={common.muted}>{l.estimatedTime} min</Text>
            </View>
            <Ionicons name={l.completed ? 'checkmark-circle' : 'ellipse-outline'} size={24}
                      color={l.completed ? colors.green : colors.gray}
                      accessibilityLabel={l.completed ? 'Completed' : 'Not completed'} />
          </Pressable>
        ))}
      </View>

      <Text style={common.h2} accessibilityRole="header">Quizzes</Text>
      <View style={styles.list}>
        {unit.quizzes.map((q) => {
          const s = stats?.get(q.id);
          return (
            <Pressable key={q.id} testID={`quiz-${q.order}`} accessibilityRole="button"
                       onPress={() => navigation.navigate('QuizEngine', { quizId: q.id })}
                       style={({ pressed }) => [common.card, styles.row, pressed && styles.pressed]}>
              <View style={styles.rowText}>
                <Text style={common.title}>{q.title}</Text>
                <Text style={common.muted}>
                  {q.questions.length} questions
                  {q.timeLimit ? `, ${Math.round(q.timeLimit / 60)} min limit` : ''}
                </Text>
              </View>
              <Text style={[styles.best, s?.bestScore == null && styles.bestNone]}>
                {s?.bestScore != null ? `Best ${Math.round(s.bestScore)}%` : 'Not taken'}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  desc: { marginTop: 4, marginBottom: 12, fontSize: 14 },
  progressRow: { flexDirection: 'row', alignItems: 'baseline', gap: 8, marginBottom: 6 },
  percent: { fontSize: 22, fontWeight: '700', color: colors.text },
  list: { gap: space.cardGap },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  rowText: { flex: 1, gap: 4 },
  best: { fontSize: 14, fontWeight: '600', color: colors.text },
  bestNone: { color: colors.muted, fontWeight: '400' },
  pressed: { opacity: 0.7 },
});
