import { DefaultTheme, NavigationContainer } from '@react-navigation/native';
import * as Crypto from 'expo-crypto';
import { SQLiteProvider, useSQLiteContext } from 'expo-sqlite';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import type { Db } from './src/db/types';
import { RootNavigator } from './src/navigation/RootNavigator';
import { AppDataProvider } from './src/state/AppData';
import { colors } from './src/theme';

export const DATABASE_NAME = 'licensure-professor.db';

const navTheme = { ...DefaultTheme, colors: { ...DefaultTheme.colors, background: colors.bg, primary: colors.primary } };
const newId = () => Crypto.randomUUID();

function WithData() {
  const db: Db = useSQLiteContext();
  return (
    <AppDataProvider db={db} newId={newId}>
      <NavigationContainer theme={navTheme}>
        <RootNavigator />
      </NavigationContainer>
    </AppDataProvider>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <SQLiteProvider databaseName={DATABASE_NAME}>
        <WithData />
      </SQLiteProvider>
    </SafeAreaProvider>
  );
}
