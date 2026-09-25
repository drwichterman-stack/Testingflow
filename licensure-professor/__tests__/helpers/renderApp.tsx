import { NavigationContainer } from '@react-navigation/native';
import { render } from '@testing-library/react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { RootNavigator } from '../../src/navigation/RootNavigator';
import { AppDataProvider } from '../../src/state/AppData';
import { createTestDb, newId } from './testDb';

export async function renderApp() {
  const db = createTestDb();
  const utils = await render(
    <SafeAreaProvider initialMetrics={{ frame: { x: 0, y: 0, width: 390, height: 844 },
                                        insets: { top: 0, left: 0, right: 0, bottom: 0 } }}>
      <AppDataProvider db={db} newId={newId} trackStudyTime={false}>
        <NavigationContainer>
          <RootNavigator />
        </NavigationContainer>
      </AppDataProvider>
    </SafeAreaProvider>,
  );
  return { db, ...utils };
}
