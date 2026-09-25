import { StyleSheet } from 'react-native';

export const colors = {
  bg: '#f4f5f7',
  surface2: '#ffffff', // card background ("surface-2" in the design)
  border: '#d6dae0',
  text: '#1c2430',
  muted: '#5f6b7a',
  primary: '#1f4e8c',
  primaryText: '#ffffff',
  green: '#1f8a4c',
  greenBg: '#e6f4ec',
  amber: '#c27c0e',
  amberBg: '#fdf3e1',
  gray: '#9aa3ad',
  track: '#e6e9ee',
  error: '#c62828',
  errorBg: '#fdecea',
  selected: '#e8f0fb',
};

export const space = { cardGap: 8, headerGap: 16, pad: 12, screen: 16 };
export const radius = 12;
export const hairline = 0.5;

export const common = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: space.screen, paddingBottom: 32 },
  card: {
    backgroundColor: colors.surface2,
    borderWidth: hairline,
    borderColor: colors.border,
    borderRadius: radius,
    padding: space.pad,
  },
  h1: { fontSize: 24, fontWeight: '700', color: colors.text },
  h2: { fontSize: 17, fontWeight: '600', color: colors.text, marginTop: 20, marginBottom: 8 },
  title: { fontSize: 16, fontWeight: '600', color: colors.text },
  body: { fontSize: 15, color: colors.text, lineHeight: 22 },
  muted: { fontSize: 13, color: colors.muted },
});
