/**
 * Autopilot View - Main container with tabs
 */

import React, { useState } from 'react';
import { AutopilotDashboard, AutopilotPositions, AutopilotActivity, AutopilotSettings } from '../../autopilot/components';

type AutopilotTab = 'dashboard' | 'positions' | 'activity' | 'settings';

interface TabButtonProps {
  id: AutopilotTab;
  label: string;
  icon: string;
  active: boolean;
  onClick: () => void;
}

const TabButton: React.FC<TabButtonProps> = ({ id, label, icon, active, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      active 
        ? 'border-blue-500 text-blue-400' 
        : 'border-transparent text-gray-400 hover:text-white hover:border-gray-600'
    }`}
    data-testid={`autopilot-tab-${id}`}
  >
    <span>{icon}</span>
    <span>{label}</span>
  </button>
);

export function AutopilotView() {
  const [activeTab, setActiveTab] = useState<AutopilotTab>('dashboard');

  const tabs: { id: AutopilotTab; label: string; icon: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '🤖' },
    { id: 'positions', label: 'Positions', icon: '📊' },
    { id: 'activity', label: 'Activity', icon: '📋' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <AutopilotDashboard />;
      case 'positions':
        return <AutopilotPositions />;
      case 'activity':
        return <AutopilotActivity />;
      case 'settings':
        return <AutopilotSettings />;
      default:
        return <AutopilotDashboard />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900" data-testid="autopilot-view">
      {/* Tab Bar */}
      <div className="flex border-b border-gray-700 bg-gray-850 px-4">
        {tabs.map((tab) => (
          <TabButton
            key={tab.id}
            id={tab.id}
            label={tab.label}
            icon={tab.icon}
            active={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
          />
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {renderContent()}
      </div>
    </div>
  );
}
