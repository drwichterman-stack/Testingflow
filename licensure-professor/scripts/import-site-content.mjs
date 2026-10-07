// Rebuilds the UNITS array in src/data/content.ts from the content bundle of thelicensureprofessor.com
// (the content/content.json that the licensure-professor-app repo's `npm run sync-content` downloads from the site).
// Only the site's own text is used; nothing is written by hand.
//
// Usage: node scripts/import-site-content.mjs path/to/content.json
//
// Mapping:
// - Each site domain (unit) becomes a unit; its lessons keep the site's lesson ids as keys.
// - Lesson text: intro, each section (## heading + paragraphs), "Terms to know" and "On the exam",
//   the same labels the site's lesson page uses.
// - The domain's question bank is split, in site order, into sets of 10 (the size of the site's
//   "Quiz me on this domain" set). Odd sets are untimed (the site's study mode); even sets are timed at the
//   site's exam pace of 67.5 seconds per item. Distractor notes, when the site has them, follow the explanation.
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SET_SIZE = 10;
const SECONDS_PER_ITEM = 67.5;

const src = process.argv[2];
if (!src) { console.error('Usage: node scripts/import-site-content.mjs path/to/content.json'); process.exit(1); }
const site = JSON.parse(readFileSync(src, 'utf8'));
const target = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'src', 'data', 'content.ts');

const s = (v) => JSON.stringify(v);
const bold = (t) => (t.includes('*') ? t : `**${t}**`);

function lessonMarkdown(l) {
  const out = [`# ${l.title}`, l.intro];
  for (const sec of l.sections) out.push(`## ${sec.h}`, ...sec.p);
  if (l.terms.length) out.push('## Terms to know', l.terms.map(([t, d]) => `- ${bold(t)}: ${d}`).join('\n'));
  if (l.tip) out.push('## On the exam', l.tip);
  return out.filter((b) => b && b.trim()).join('\n\n');
}

function explanation(q) {
  const notes = (q.why ?? []).map((w, i) => (w && i !== q.ans ? `${'ABCD'[i]}. ${w}` : null)).filter(Boolean);
  return [q.exp, ...notes].join('\n');
}

const areaShort = Object.fromEntries(site.areas.map((a) => [a.key, a.short]));
const lines = ['const UNITS: UnitSpec[] = ['];
for (const u of site.units) {
  const pool = site.questions.filter((q) => q.area === u.key);
  lines.push('  {', `    key: ${s(u.key)},`, `    title: ${s(u.title)},`, `    description: ${s(u.blurb)},`, '    lessons: [');
  for (const l of u.lessons) {
    lines.push('      {', `        key: ${s(l.id)},`, `        title: ${s(l.title)},`, `        minutes: ${l.minutes},`,
      `        content: ${s(lessonMarkdown(l))},`, '      },');
  }
  lines.push('    ],', '    quizzes: [');
  for (let i = 0, n = 1; i < pool.length; i += SET_SIZE, n++) {
    const qs = pool.slice(i, i + SET_SIZE);
    const timed = n % 2 === 0;
    lines.push('      {', `        key: ${s(`${u.key}.set${n}`)},`,
      `        title: ${s(`${areaShort[u.key] ?? u.title} · Set ${n}${timed ? ' (timed)' : ''}`)},`,
      `        timeLimit: ${timed ? Math.round(qs.length * SECONDS_PER_ITEM) : 'null'},`, '        questions: [');
    for (const q of qs) {
      lines.push('          {', `            text: ${s(q.q)},`, `            options: ${s(q.choices)},`,
        `            answer: ${q.ans},`, `            explanation: ${s(explanation(q))},`, '          },');
    }
    lines.push('        ],', '      },');
  }
  lines.push('    ],', '  },');
}
lines.push('];');

const ts = readFileSync(target, 'utf8');
const start = ts.indexOf('const UNITS: UnitSpec[] = [');
const end = ts.indexOf('\n];\n', start);
if (start < 0 || end < 0) throw new Error('UNITS array not found in content.ts');
writeFileSync(target, ts.slice(0, start) + lines.join('\n') + ts.slice(end + 3));
const q = site.units.map((u) => site.questions.filter((x) => x.area === u.key).length);
console.log(`Wrote ${site.units.length} units, ${site.units.reduce((a, u) => a + u.lessons.length, 0)} lessons, ` +
  `${q.reduce((a, n) => a + Math.ceil(n / SET_SIZE), 0)} quizzes, ${q.reduce((a, n) => a + n, 0)} questions (site sync ${site.syncedAt}).`);
