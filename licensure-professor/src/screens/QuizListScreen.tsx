import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import * as repo from '../db/repo';
import type { QuizStackParams } from '../navigation/types';
import { useCourses, useLoader } from '../state/AppData';
import { colors, common, space } from '../theme';

type Props = NativeStackScreenProps<QuizStackParams, 'QuizList'>;

export function QuizListScreen({ navigation }: Props) {
  const courses = useCourses();
  const stats = useLoader((a) => repo.quizStats(a.db, a.userId));
  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <Text style={common.h1}>Quizzes</Text>
      <Text style={[common.muted, { marginTop: 2 }]}>Practice questions by unit. Passing score is 70%.</Text>
      {(courses ?? []).map((c) => (
        <View key={c.id}>
          <Text style={common.h2}>{c.title}</Text>
          <View style={{ gap: space.cardGap }}>
            {c.quizzes.map((q) => {
              const s = stats?.get(q.id);
              return (
                <Pressable key={q.id} testID={`quizlist-${q.id}`} accessibilityRole="button"
                           onPress={() => navigation.navigate('QuizEngine', { quizId: q.id })}
                           style={({ pressed }) => [common.card, styles.row, pressed && { opacity: 0.7 }]}>
                  <View style={{ flex: 1, gap: 4 }}>
                    <Text style={common.title}>{q.title}</Text>
                    <Text style={common.muted}>
                      {q.questions.length} questions
                      {q.timeLimit ? `, ${Math.round(q.timeLimit / 60)} min limit` : ', untimed'}
                      {s ? `, ${s.attempts} attempt${s.attempts === 1 ? '' : 's'}` : ''}
                    </Text>
                  </View>
                  <Text style={[styles.best, !s && styles.none]}>
                    {s?.bestScore != null ? `${Math.round(s.bestScore)}%` : '-'}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  best: { fontSize: 18, fontWeight: '700', color: colors.text },
  none: { color: colors.gray },
});
