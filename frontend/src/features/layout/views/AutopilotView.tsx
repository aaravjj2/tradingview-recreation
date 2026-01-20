/**
 * Autopilot View - Main container
 */

import React from 'react';
import { AutopilotDashboard } from '../../autopilot/components';

export function AutopilotView() {
  return (
    <div className="h-full w-full">
      <AutopilotDashboard />
    </div>
  );
}
