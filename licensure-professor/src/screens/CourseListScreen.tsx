import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ProgressBar } from '../components/ProgressBar';
import * as repo from '../db/repo';
import { formatStudyTime } from '../logic/progress';
import type { HomeStackParams } from '../navigation/types';
import { useCourses, useLoader } from '../state/AppData';
import { colors, common, space } from '../theme';

type Props = NativeStackScreenProps<HomeStackParams, 'CourseList'>;

export function CourseListScreen({ navigation }: Props) {
  const courses = useCourses();
  const week = useLoader((a) => repo.weeklyStudySeconds(a.db, a.userId, new Date()));
  const overall = courses ? repo.overallFromCourses(courses) : 0;

  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <Text style={common.h1} accessibilityRole="header">NCE Exam Prep</Text>
      <Text style={[common.muted, styles.subtitle]}>{"Master's/Doctoral Counseling"}</Text>

      <View style={styles.stats}>
        <View style={[common.card, styles.stat]}>
          <Text style={common.muted}>This week</Text>
          <Text style={styles.statValue} testID="stat-week">{formatStudyTime(week ?? 0)}</Text>
          <Text style={common.muted}>hours studied</Text>
        </View>
        <View style={[common.card, styles.stat]}>
          <Text style={common.muted}>Overall</Text>
          <Text style={styles.statValue} testID="stat-overall">{overall}%</Text>
          <Text style={common.muted}>score</Text>
        </View>
      </View>

      <View style={styles.list}>
        {(courses ?? []).map((c) => (
          <Pressable key={c.id} testID={`unit-${c.id}`} accessibilityRole="button"
                     onPress={() => navigation.navigate('UnitDetail', { unitId: c.id })}
                     style={({ pressed }) => [common.card, styles.unit, pressed && styles.pressed]}>
            <View style={styles.unitText}>
              <Text style={common.title}>{c.title}</Text>
              <Text style={common.muted}>
                {c.totalLessons} lessons, {c.totalQuizzes} quizzes
              </Text>
            </View>
            <View style={styles.unitScore}>
              <Text style={styles.percent}>{c.progressPercentage}%</Text>
              <ProgressBar percent={c.progressPercentage} />
            </View>
          </Pressable>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  subtitle: { marginTop: 2, marginBottom: space.headerGap, fontSize: 14 },
  stats: { flexDirection: 'row', gap: space.cardGap, marginBottom: space.headerGap },
  stat: { flex: 1 },
  statValue: { fontSize: 24, fontWeight: '700', color: colors.text, marginVertical: 4 },
  list: { gap: space.cardGap },
  unit: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  unitText: { flex: 1, gap: 4 },
  unitScore: { width: 84, alignItems: 'flex-end', gap: 6 },
  percent: { fontSize: 22, fontWeight: '700', color: colors.text },
  pressed: { opacity: 0.7 },
});
