# The Licensure Professor

NCE exam prep for master's and doctoral counseling students. React Native with Expo (SDK 57), for iOS and Android from one codebase. Works fully offline: all content is bundled and all progress is stored on the device in SQLite.

## Quick start

Requirements: Node.js 20 or newer, and either the **Expo Go** app on a phone, Xcode (iOS Simulator, Mac only), or Android Studio (Android Emulator).

```bash
cd licensure-professor
npm install
npx expo start
```

Then press:

- `i` to open the iOS Simulator (Mac with Xcode installed),
- `a` to open the Android Emulator (start an emulator in Android Studio first), or
- scan the QR code with Expo Go (Android) or the Camera app (iPhone).

Every native module the app uses (expo-sqlite, expo-crypto, screens, safe area) is included in Expo Go. No development build is needed to try the app.

## Checks

```bash
npm test            # 32 Jest tests: logic, content, database, and full-app UI flows
npm run typecheck   # TypeScript for the app and the tests
npm run lint        # ESLint (eslint-config-expo)
```

The database tests run the app's real SQL against Node's built-in SQLite (Node 22.5 or newer). The UI tests render the whole app (tabs, stacks, screens) with React Native Testing Library against that database.

## Building for the App Store and Google Play

Builds run on Expo's cloud service (EAS). You need a free Expo account, an **Apple Developer Program** membership (for iOS), and a **Google Play Console** account (for Android).

1. Sign in and link the project (first time only):
   ```bash
   npx eas-cli@latest login
   npx eas-cli@latest init        # creates the EAS project and writes its id into app.json
   ```
2. Check the app identifiers in `app.json`: `ios.bundleIdentifier` and `android.package` are set to `com.thelicensureprofessor.app`. Change them now if you want a different id; they cannot change after the first store upload.
3. Build:
   ```bash
   npm run build:ios         # production .ipa, for TestFlight and the App Store
   npm run build:android     # production .aab, for Google Play
   ```
   On the first iOS build EAS asks for your Apple ID and can create the certificate and provisioning profile for you. On the first Android build it can generate and store the upload keystore. **Keep that keystore:** Google Play requires the same key for every update.
4. Submit (optional; you can also upload by hand):
   ```bash
   npx eas-cli@latest submit --platform ios       # to App Store Connect / TestFlight
   npx eas-cli@latest submit --platform android   # to Google Play (needs a service account key)
   ```

### Builds for simulators and test devices

```bash
npm run build:sim   # iOS Simulator build (.app in a .tar.gz); drag it onto a running simulator
npm run build:apk   # Android .apk; drag it onto a running emulator or install with adb
```

Profiles are defined in `eas.json`:

| Profile | iOS | Android | Use |
|---|---|---|---|
| `development` | Simulator build | `.apk` | Simulator and emulator testing |
| `preview` | Ad hoc build for registered devices | `.apk` | Internal testers |
| `production` | `.ipa` | `.aab` | TestFlight, App Store, Google Play |

Before each store release, raise `version` (and `ios.buildNumber` and `android.versionCode`) in `app.json`.

## What the app does

| Tab | Screens |
|---|---|
| **Home** | Course list with this week's study time, overall score, and the 3 units (score and progress bar: green above 70%, amber 40% to 70%, gray below 40%). Unit detail with lessons (time, checkmark) and quizzes (question count, time limit, best score). Lesson viewer with "X of Y", Prev/Next, "Mark as complete", and "Next lesson". |
| **Quizzes** | All quizzes by unit, with attempts and best score. The quiz engine: unit and quiz title, "4 of 8" counter, countdown timer on timed quizzes, progress bar, lettered radio options. |
| **Progress** | Overall score and a per-unit breakdown. Tap a unit for lessons completed, average quiz score, attempts, and time spent in quizzes. |
| **Settings** | Offline status, reset progress, and app information. |

### Quiz rules

- **Submit is blocked** until an answer is selected. Tapping Submit with no selection shows "Select an answer to continue" in red (13px) under the options. Selecting any option clears it.
- After submitting, the correct option is highlighted green, a wrong choice red, and the explanation is shown. The answer is **saved to SQLite at once**.
- Next moves to the next question; after the last one the Quiz Complete screen shows the score, a PASSED or NOT PASSED badge, a per-question breakdown, and **Review answers**, **Return to unit**, and **Retake quiz**.
- **Timed quizzes** count down from the start of the attempt. When time runs out the quiz ends, and unanswered questions count as incorrect.
- Passing score is 70%. An attempt left unfinished does not count toward scores.

### Progress calculation

- **Unit score** = 50% x (lessons completed / total lessons) + 50% x (average quiz score).
- The average quiz score uses each quiz's **best** completed score, and a quiz not yet taken counts as 0. This way a unit only reaches 100% when every lesson is done and every quiz is aced. (The specification did not say how untaken quizzes count; change `unitPercent` in `src/logic/progress.ts` if you prefer to average only the quizzes taken.)
- **Overall score** = the mean of the unit scores.
- **Study time** is the time the app is open in the foreground. Each stretch is one session, saved every 30 seconds and when the app goes to the background. "This week" starts on Monday.

## Updating the course content

`src/data/content.ts` holds the NCE course from thelicensureprofessor.com: 6 units (the six NCE domains), 64 lessons, and 1003 practice questions in 102 quizzes. Its `UNITS` array is generated from the site's content bundle, `content/content.json` in the licensure-professor-app repository (refreshed there with `npm run sync-content`). Do not edit `UNITS` by hand; change the content on the website, then regenerate:

```bash
node scripts/import-site-content.mjs ../licensure-professor-app/content/content.json
```

- Units and lessons keep the site's keys (for example `ethics` and `ethics/the-counseling-profession`), and IDs are derived from them, so students keep their progress across updates.
- Lesson text is the site's intro, sections, "Terms to know" and "On the exam", in a small markdown subset: `# ` and `## ` headings, paragraphs, `- ` bullets, and `**bold**`.
- Each domain's questions are split, in site order, into sets of 10. Odd sets are untimed; even sets are timed at the site's exam pace of 67.5 seconds per item. The site's notes on wrong choices follow the explanation, lettered to match the options.
- Not imported: lesson videos (the app makes no network requests), flashcards, the baseline and full-length forms, and the NCMHCE material.
- After regenerating, increase `CONTENT_VERSION`. On next launch the app reloads the content and leaves progress untouched.

## Project layout

```
App.tsx                     SQLite provider, data provider, navigation container
src/types.ts                data model (Course, Lesson, Quiz, Question, UserProgress, QuizAttempt)
src/data/content.ts         bundled course content (generated)
scripts/import-site-content.mjs  rebuilds the content from the site bundle
src/db/schema.ts            SQLite schema (content and progress tables)
src/db/repo.ts              all reads and writes; progress is written immediately
src/db/types.ts             the small database interface used by the app and tests
src/logic/progress.ts       score, color, and time calculations
src/logic/quizMachine.ts    quiz state machine (select, submit validation, next, timeout)
src/state/AppData.tsx       Context API state, study-time sessions, data loaders
src/navigation/             bottom tabs and native stacks (React Navigation 7)
src/screens/                one file per screen
src/components/             progress bar, lesson markdown renderer
__tests__/                  Jest and React Native Testing Library tests
eas.json                    EAS build profiles
```

## Privacy and offline behavior

- The app makes **no network requests**. Content ships inside the app, so nothing is downloaded after installation.
- Progress stays on the device in `licensure-professor.db`. The only identifier is a random ID generated on first launch. There is no account, no analytics, and no cloud sync.
- Deleting the app deletes the progress. **Settings > Reset progress** clears it without deleting content.
- `ios.infoPlist.ITSAppUsesNonExemptEncryption` is `false` because the app uses no encryption beyond the operating system's own. This skips the export-compliance question on each TestFlight upload.
