import type { NavigatorScreenParams } from '@react-navigation/native';

export type HomeStackParams = {
  CourseList: undefined;
  UnitDetail: { unitId: string };
  LessonViewer: { unitId: string; lessonId: string };
  QuizEngine: { quizId: string };
};

export type QuizStackParams = {
  QuizList: undefined;
  QuizEngine: { quizId: string };
};

export type ProgressStackParams = {
  StatsOverview: undefined;
  DetailedProgress: { unitId: string };
};

export type SettingsStackParams = {
  Settings: undefined;
};

export type TabParams = {
  HomeTab: NavigatorScreenParams<HomeStackParams>;
  QuizTab: NavigatorScreenParams<QuizStackParams>;
  ProgressTab: NavigatorScreenParams<ProgressStackParams>;
  SettingsTab: NavigatorScreenParams<SettingsStackParams>;
};
