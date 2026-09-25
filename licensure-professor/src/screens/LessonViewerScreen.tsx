import Ionicons from '@expo/vector-icons/Ionicons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useEffect, useRef } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Markdown } from '../components/Markdown';
import * as repo from '../db/repo';
import type { HomeStackParams } from '../navigation/types';
import { useAppData, useCourses } from '../state/AppData';
import { colors, common, hairline, radius } from '../theme';

type Props = NativeStackScreenProps<HomeStackParams, 'LessonViewer'>;

export function LessonViewerScreen({ navigation, route }: Props) {
  const app = useAppData();
  const insets = useSafeAreaInsets();
  const scroll = useRef<ScrollView>(null);
  const courses = useCourses();
  const unit = courses?.find((c) => c.id === route.params.unitId);
  const index = unit ? unit.lessons.findIndex((l) => l.id === route.params.lessonId) : -1;
  const lesson = unit && index >= 0 ? unit.lessons[index] : undefined;

  useEffect(() => {
    if (lesson) {
      navigation.setOptions({ title: lesson.title });
      scroll.current?.scrollTo({ y: 0, animated: false });
      repo.touchCourse(app.db, app.userId, lesson.unitId);
    }
  }, [lesson?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!unit || !lesson) return <View style={common.screen} />;
  const total = unit.lessons.length;
  const go = (i: number) => navigation.setParams({ lessonId: unit.lessons[i].id });

  const toggleComplete = async () => {
    await repo.setLessonComplete(app.db, app.userId, lesson.id, !lesson.completed);
    app.refresh();
  };
  const completeAndNext = async () => {
    if (!lesson.completed) await repo.setLessonComplete(app.db, app.userId, lesson.id, true);
    app.refresh();
    if (index < total - 1) go(index + 1);
    else navigation.goBack();
  };

  return (
    <View style={common.screen}>
      <View style={styles.bar}>
        <Pressable onPress={() => go(index - 1)} disabled={index === 0} testID="lesson-prev"
                   accessibilityRole="button" accessibilityLabel="Previous lesson"
                   style={[styles.navBtn, index === 0 && styles.disabled]}>
          <Ionicons name="chevron-back" size={18} color={colors.primary} />
          <Text style={styles.navText}>Prev</Text>
        </Pressable>
        <Text style={styles.counter} testID="lesson-counter">{index + 1} of {total}</Text>
        <Pressable onPress={() => go(index + 1)} disabled={index === total - 1} testID="lesson-next"
                   accessibilityRole="button" accessibilityLabel="Next lesson"
                   style={[styles.navBtn, index === total - 1 && styles.disabled]}>
          <Text style={styles.navText}>Next</Text>
          <Ionicons name="chevron-forward" size={18} color={colors.primary} />
        </Pressable>
      </View>

      <ScrollView ref={scroll} contentContainerStyle={common.content}>
        <View style={styles.meta}>
          <Ionicons name="time-outline" size={16} color={colors.muted} />
          <Text style={common.muted}>{lesson.estimatedTime} min read</Text>
          {lesson.completed && (
            <>
              <Ionicons name="checkmark-circle" size={16} color={colors.green} />
              <Text style={[common.muted, { color: colors.green }]}>Completed</Text>
            </>
          )}
        </View>
        <Markdown source={lesson.content} />
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: 12 + insets.bottom }]}>
        <Pressable onPress={toggleComplete} testID="lesson-complete" accessibilityRole="button"
                   style={[styles.btn, lesson.completed ? styles.btnDone : styles.btnOutline]}>
          <Text style={[styles.btnText, { color: lesson.completed ? colors.green : colors.primary }]}>
            {lesson.completed ? '✓ Completed' : 'Mark as complete'}
          </Text>
        </Pressable>
        <Pressable onPress={completeAndNext} testID="lesson-complete-next" accessibilityRole="button"
                   style={[styles.btn, styles.btnPrimary]}>
          <Text style={[styles.btnText, { color: colors.primaryText }]}>
            {index < total - 1 ? 'Next lesson' : 'Finish unit lessons'}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
         paddingHorizontal: 12, paddingVertical: 8, backgroundColor: colors.surface2,
         borderBottomWidth: hairline, borderColor: colors.border },
  navBtn: { flexDirection: 'row', alignItems: 'center', padding: 6, minWidth: 70 },
  navText: { color: colors.primary, fontSize: 15, fontWeight: '600' },
  disabled: { opacity: 0.3 },
  counter: { fontSize: 14, color: colors.muted, fontWeight: '600' },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 12 },
  footer: { flexDirection: 'row', gap: 8, paddingHorizontal: 16, paddingTop: 12,
            backgroundColor: colors.surface2, borderTopWidth: hairline, borderColor: colors.border },
  btn: { flex: 1, borderRadius: radius, paddingVertical: 13, alignItems: 'center' },
  btnPrimary: { backgroundColor: colors.primary },
  btnOutline: { borderWidth: 1, borderColor: colors.primary },
  btnDone: { borderWidth: 1, borderColor: colors.green, backgroundColor: colors.greenBg },
  btnText: { fontSize: 15, fontWeight: '600' },
});
