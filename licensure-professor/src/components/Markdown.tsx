/**
 * Renders the lesson markdown subset: "# " and "## " headings, paragraphs,
 * "- " bullet lists, and **bold**. No external library and no WebView, so
 * lessons render offline and identically on iOS and Android.
 */
import { Fragment } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';

export type Block =
  | { kind: 'h1' | 'h2' | 'p'; text: string }
  | { kind: 'ul'; items: string[] };

export function parseMarkdown(src: string): Block[] {
  const blocks: Block[] = [];
  let para: string[] = [];
  let list: string[] | null = null;
  const flush = () => {
    if (para.length) blocks.push({ kind: 'p', text: para.join(' ') });
    if (list) blocks.push({ kind: 'ul', items: list });
    para = [];
    list = null;
  };
  for (const raw of src.split('\n')) {
    const line = raw.trim();
    if (!line) { flush(); continue; }
    if (line.startsWith('## ')) { flush(); blocks.push({ kind: 'h2', text: line.slice(3) }); continue; }
    if (line.startsWith('# ')) { flush(); blocks.push({ kind: 'h1', text: line.slice(2) }); continue; }
    if (line.startsWith('- ')) {
      if (para.length) { blocks.push({ kind: 'p', text: para.join(' ') }); para = []; }
      (list ??= []).push(line.slice(2));
      continue;
    }
    if (list) { blocks.push({ kind: 'ul', items: list }); list = null; }
    para.push(line);
  }
  flush();
  return blocks;
}

function Inline({ text, style }: { text: string; style: object }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return (
    <Text style={style}>
      {parts.map((p, i) => p.startsWith('**') && p.endsWith('**')
        ? <Text key={i} style={styles.bold}>{p.slice(2, -2)}</Text>
        : <Fragment key={i}>{p}</Fragment>)}
    </Text>
  );
}

export function Markdown({ source, skipFirstHeading = false }: { source: string; skipFirstHeading?: boolean }) {
  let blocks = parseMarkdown(source);
  if (skipFirstHeading && blocks[0]?.kind === 'h1') blocks = blocks.slice(1);
  return (
    <View>
      {blocks.map((b, i) => {
        if (b.kind === 'ul') {
          return (
            <View key={i} style={styles.list}>
              {b.items.map((it, j) => (
                <View key={j} style={styles.li}>
                  <Text style={styles.bullet}>{'•'}</Text>
                  <Inline text={it} style={styles.liText} />
                </View>
              ))}
            </View>
          );
        }
        return <Inline key={i} text={b.text} style={styles[b.kind]} />;
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 22, fontWeight: '700', color: colors.text, marginBottom: 12 },
  h2: { fontSize: 17, fontWeight: '700', color: colors.text, marginTop: 18, marginBottom: 6 },
  p: { fontSize: 16, lineHeight: 24, color: colors.text, marginBottom: 10 },
  bold: { fontWeight: '700' },
  list: { marginBottom: 10 },
  li: { flexDirection: 'row', marginBottom: 6, paddingRight: 8 },
  bullet: { fontSize: 16, lineHeight: 24, width: 18, color: colors.muted },
  liText: { flex: 1, fontSize: 16, lineHeight: 24, color: colors.text },
});
