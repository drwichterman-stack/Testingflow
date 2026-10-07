import { StyleSheet, View } from 'react-native';
import { progressTone } from '../logic/progress';
import { colors } from '../theme';

const TONE = { green: colors.green, amber: colors.amber, gray: colors.gray };

interface Props {
  percent: number;
  /** Fixed fill color; defaults to the green/amber/gray tone for the percentage. */
  color?: string;
  height?: number;
  testID?: string;
}

export function ProgressBar({ percent, color, height = 6, testID }: Props) {
  const p = Math.max(0, Math.min(100, percent));
  return (
    <View style={[styles.track, { height, borderRadius: height / 2 }]} testID={testID}
          accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: p }}>
      <View style={{ width: `${p}%`, height, borderRadius: height / 2,
                     backgroundColor: color ?? TONE[progressTone(p)] }} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: { backgroundColor: colors.track, overflow: 'hidden', width: '100%' },
});
