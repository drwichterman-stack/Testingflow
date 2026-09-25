import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import * as repo from '../db/repo';
import { useAppData } from '../state/AppData';
import { colors, common, space } from '../theme';
import appConfig from '../../app.json';

export function SettingsScreen() {
  const app = useAppData();
  const reset = () => {
    Alert.alert('Reset all progress?',
      'This deletes completed lessons, quiz attempts, and study time on this device. Course content stays.',
      [{ text: 'Cancel', style: 'cancel' },
       { text: 'Reset', style: 'destructive', onPress: async () => {
           await repo.resetProgress(app.db);
           await app.restartStudySession();
           app.refresh();
         } }]);
  };
  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <Text style={[common.h1, { marginBottom: space.headerGap }]}>Settings</Text>

      <View style={[common.card, styles.block]}>
        <Text style={common.title}>Offline</Text>
        <Text style={common.body}>
          All lessons and quizzes are stored on this device. The app never needs a network connection,
          and your progress is saved only on this device.
        </Text>
      </View>

      <View style={[common.card, styles.block]}>
        <Text style={common.title}>Data</Text>
        <Pressable onPress={reset} testID="btn-reset" accessibilityRole="button" style={styles.danger}>
          <Text style={styles.dangerText}>Reset progress</Text>
        </Pressable>
      </View>

      <View style={[common.card, styles.block]}>
        <Text style={common.title}>About</Text>
        <Text style={common.body}>The Licensure Professor</Text>
        <Text style={common.muted}>{"NCE exam prep for master's and doctoral counseling students."}</Text>
        <Text style={common.muted}>Version {appConfig.expo.version}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  block: { gap: 8, marginBottom: space.cardGap },
  danger: { borderWidth: 1, borderColor: colors.error, borderRadius: 10, paddingVertical: 12, alignItems: 'center' },
  dangerText: { color: colors.error, fontSize: 15, fontWeight: '600' },
});
