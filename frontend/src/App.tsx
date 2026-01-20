import { useEffect } from 'react';
import { Shell } from './features/layout/shell/Shell';
import { ClockClient } from './data/ClockClient';

import { WebSocketClient } from './data/WebSocketClient';

function App() {
  useEffect(() => {
    // Check for deterministic E2E mode
    const params = new URLSearchParams(window.location.search);
    if (params.get('e2e') === '1') {
      console.log('ENTERED E2E MODE');
      document.body.classList.add('e2e-mode');

      // Force virtual clock to ensure time is deterministic
      ClockClient.setMode('virtual', 1672531200000).catch(console.error); // 2023-01-01

      // Fast-fail WebSockets for E2E speed
      WebSocketClient.overrideThresholds(2000, 3000);
    }
  }, []);

  return (
    <Shell />
  );
}

export default App;
