import React, { useState } from 'react';
import { Header } from './Header';
import { cn } from "../../../lib/utils";
import ResearchTab from '../tabs/ResearchTab';
import PMsTab from '../tabs/PMsTab';
import CouncilTab from '../tabs/CouncilTab';
import TradesTab from '../tabs/TradesTab';
import MonitorTab from '../tabs/MonitorTab';
import SettingsTab from '../tabs/SettingsTab';

export function DashboardLayout() {
  const [activeTab, setActiveTab] = useState('research');
  const [mode, setMode] = useState('MANUAL');

  const tabs = [
    { id: 'research', label: 'Research' },
    { id: 'pms', label: 'PMs' },
    { id: 'council', label: 'Council' },
    { id: 'trades', label: 'Trades' },
    { id: 'monitor', label: 'Monitor' },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header mode={mode} setMode={setMode} />
      
      <div className="border-b bg-muted/40">
        <div className="flex px-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "px-6 py-3 text-sm font-medium border-b-2 transition-colors",
                activeTab === tab.id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <main className="flex-1 p-6">
        {activeTab === 'research' && <ResearchTab />}
        {activeTab === 'pms' && <PMsTab />}
        {activeTab === 'council' && <CouncilTab />}
        {activeTab === 'trades' && <TradesTab />}
        {activeTab === 'monitor' && <MonitorTab />}
        {activeTab === 'settings' && <SettingsTab />}
      </main>
    </div>
  );
}
