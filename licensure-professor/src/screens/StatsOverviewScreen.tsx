import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ProgressBar } from '../components/ProgressBar';
import * as repo from '../db/repo';
import { formatStudyTime } from '../logic/progress';
import type { ProgressStackParams } from '../navigation/types';
import { useCourses, useLoader } from '../state/AppData';
import { colors, common, space } from '../theme';

type Props = NativeStackScreenProps<ProgressStackParams, 'StatsOverview'>;

export function StatsOverviewScreen({ navigation }: Props) {
  const courses = useCourses();
  const total = useLoader((a) => repo.studySeconds(a.db, a.userId));
  const overall = courses ? repo.overallFromCourses(courses) : 0;
  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <Text style={[common.h1, { marginBottom: space.headerGap }]}>Progress</Text>
      <View style={[common.card, { gap: 6 }]}>
        <Text style={common.muted}>Overall score</Text>
        <Text style={styles.big} testID="overall-score">{overall}%</Text>
        <ProgressBar percent={overall} height={8} />
        <Text style={[common.muted, { marginTop: 4 }]}>
          Total study time {formatStudyTime(total ?? 0)} hours
        </Text>
      </View>

      <Text style={common.h2} accessibilityRole="header">By unit</Text>
      <View style={{ gap: space.cardGap }}>
        {(courses ?? []).map((c) => (
          <Pressable key={c.id} testID={`progress-unit-${c.id}`} accessibilityRole="button"
                     onPress={() => navigation.navigate('DetailedProgress', { unitId: c.id })}
                     style={({ pressed }) => [common.card, { gap: 8 }, pressed && { opacity: 0.7 }]}>
            <View style={styles.row}>
              <Text style={[common.title, { flex: 1 }]}>{c.title}</Text>
              <Text style={styles.pct}>{c.progressPercentage}%</Text>
            </View>
            <ProgressBar percent={c.progressPercentage} />
          </Pressable>
        ))}
      </View>
      <Text style={[common.muted, { marginTop: 12 }]}>
        Unit score = half lesson completion, half average of best quiz scores (quizzes not yet taken count as 0).
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  big: { fontSize: 24, fontWeight: '700', color: colors.text },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  pct: { fontSize: 16, fontWeight: '700', color: colors.text, textAlign: 'right' },
});
