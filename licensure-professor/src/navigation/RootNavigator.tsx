import Ionicons from '@expo/vector-icons/Ionicons';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { CourseListScreen } from '../screens/CourseListScreen';
import { DetailedProgressScreen } from '../screens/DetailedProgressScreen';
import { LessonViewerScreen } from '../screens/LessonViewerScreen';
import { QuizEngineScreen } from '../screens/QuizEngineScreen';
import { QuizListScreen } from '../screens/QuizListScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { StatsOverviewScreen } from '../screens/StatsOverviewScreen';
import { UnitDetailScreen } from '../screens/UnitDetailScreen';
import { colors } from '../theme';
import type { HomeStackParams, ProgressStackParams, QuizStackParams, SettingsStackParams, TabParams } from './types';

const Tab = createBottomTabNavigator<TabParams>();
const HomeStack = createNativeStackNavigator<HomeStackParams>();
const QuizStack = createNativeStackNavigator<QuizStackParams>();
const ProgressStack = createNativeStackNavigator<ProgressStackParams>();
const SettingsStack = createNativeStackNavigator<SettingsStackParams>();

const stackOptions = {
  headerTintColor: colors.primary,
  headerTitleStyle: { color: colors.text },
  headerStyle: { backgroundColor: colors.surface2 },
  contentStyle: { backgroundColor: colors.bg },
  headerBackButtonDisplayMode: 'minimal' as const,
};

function HomeTab() {
  return (
    <HomeStack.Navigator screenOptions={stackOptions}>
      <HomeStack.Screen name="CourseList" component={CourseListScreen} options={{ headerShown: false }} />
      <HomeStack.Screen name="UnitDetail" component={UnitDetailScreen} options={{ title: 'Unit' }} />
      <HomeStack.Screen name="LessonViewer" component={LessonViewerScreen} options={{ title: 'Lesson' }} />
      <HomeStack.Screen name="QuizEngine" component={QuizEngineScreen} options={{ title: 'Quiz' }} />
    </HomeStack.Navigator>
  );
}

function QuizTab() {
  return (
    <QuizStack.Navigator screenOptions={stackOptions}>
      <QuizStack.Screen name="QuizList" component={QuizListScreen} options={{ headerShown: false }} />
      <QuizStack.Screen name="QuizEngine" component={QuizEngineScreen} options={{ title: 'Quiz' }} />
    </QuizStack.Navigator>
  );
}

function ProgressTab() {
  return (
    <ProgressStack.Navigator screenOptions={stackOptions}>
      <ProgressStack.Screen name="StatsOverview" component={StatsOverviewScreen} options={{ headerShown: false }} />
      <ProgressStack.Screen name="DetailedProgress" component={DetailedProgressScreen} options={{ title: 'Unit progress' }} />
    </ProgressStack.Navigator>
  );
}

function SettingsTab() {
  return (
    <SettingsStack.Navigator screenOptions={stackOptions}>
      <SettingsStack.Screen name="Settings" component={SettingsScreen} options={{ headerShown: false }} />
    </SettingsStack.Navigator>
  );
}

const ICONS: Record<keyof TabParams, [keyof typeof Ionicons.glyphMap, keyof typeof Ionicons.glyphMap]> = {
  HomeTab: ['home', 'home-outline'],
  QuizTab: ['help-circle', 'help-circle-outline'],
  ProgressTab: ['stats-chart', 'stats-chart-outline'],
  SettingsTab: ['settings', 'settings-outline'],
};

export function RootNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.muted,
        tabBarIcon: ({ focused, color, size }) => (
          <Ionicons name={ICONS[route.name][focused ? 0 : 1]} size={size} color={color} />
        ),
      })}>
      <Tab.Screen name="HomeTab" component={HomeTab} options={{ title: 'Home' }} />
      <Tab.Screen name="QuizTab" component={QuizTab} options={{ title: 'Quizzes' }} />
      <Tab.Screen name="ProgressTab" component={ProgressTab} options={{ title: 'Progress' }} />
      <Tab.Screen name="SettingsTab" component={SettingsTab} options={{ title: 'Settings' }} />
    </Tab.Navigator>
  );
}
