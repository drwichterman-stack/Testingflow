import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useEffect } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { ProgressBar } from '../components/ProgressBar';
import * as repo from '../db/repo';
import { formatStudyTime } from '../logic/progress';
import type { ProgressStackParams } from '../navigation/types';
import { useCourses, useLoader } from '../state/AppData';
import { colors, common, space } from '../theme';

type Props = NativeStackScreenProps<ProgressStackParams, 'DetailedProgress'>;

export function DetailedProgressScreen({ navigation, route }: Props) {
  const courses = useCourses();
  const unit = courses?.find((c) => c.id === route.params.unitId);
  const summary = useLoader(async (a) => (unit ? repo.unitStudySummary(a.db, a.userId, unit) : null),
                            unit);
  useEffect(() => {
    if (unit) navigation.setOptions({ title: unit.title.split(':')[0] });
  }, [unit?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!unit) return <View style={common.screen} />;
  const done = unit.lessons.filter((l) => l.completed).length;
  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <Text style={common.h1}>{unit.title}</Text>
      <View style={[common.card, { gap: 6, marginTop: space.headerGap }]}>
        <Text style={common.muted}>Unit score</Text>
        <Text style={styles.big}>{unit.progressPercentage}%</Text>
        <ProgressBar percent={unit.progressPercentage} height={8} />
      </View>
      <View style={styles.grid}>
        <Stat label="Lessons completed" value={`${done} of ${unit.totalLessons}`} />
        <Stat label="Average quiz score" value={summary?.averageScore != null ? `${summary.averageScore}%` : '-'} />
        <Stat label="Quiz attempts" value={String(summary?.attempts ?? 0)} />
        <Stat label="Time in quizzes" value={formatStudyTime(summary?.quizSeconds ?? 0)} />
      </View>
      <Text style={common.muted}>
        Reading time of completed lessons: {summary?.lessonMinutesCompleted ?? 0} min (estimated).
      </Text>

      <Text style={common.h2}>Quizzes</Text>
      <View style={{ gap: space.cardGap }}>
        {(summary?.perQuiz ?? []).map(({ quiz, stats }) => (
          <View key={quiz.id} style={[common.card, styles.row]}>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={common.title}>{quiz.title}</Text>
              <Text style={common.muted}>
                {stats ? `${stats.attempts} attempt${stats.attempts === 1 ? '' : 's'}, last ${Math.round(stats.lastScore ?? 0)}%`
                       : 'Not taken yet'}
              </Text>
            </View>
            <Text style={styles.best}>{stats?.bestScore != null ? `Best ${Math.round(stats.bestScore)}%` : '-'}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={[common.card, styles.stat]}>
      <Text style={common.muted}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  big: { fontSize: 24, fontWeight: '700', color: colors.text },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.cardGap, marginVertical: 12 },
  stat: { flexBasis: '48%', flexGrow: 1, gap: 4 },
  statValue: { fontSize: 18, fontWeight: '700', color: colors.text },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  best: { fontSize: 14, fontWeight: '600', color: colors.text },
});
