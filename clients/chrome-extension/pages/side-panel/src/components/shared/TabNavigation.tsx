import React from 'react';

export type TabId = 'chat' | 'data-sources';

interface Tab {
  id: TabId;
  label: string;
}

interface TabNavigationProps {
  activeTab: TabId;
  onTabChange: (tabId: TabId) => void;
}

const tabs: Tab[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'data-sources', label: 'Data Sources' },
];

export function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  return (
    <div className="flex border-b border-gray-200 bg-white">
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`
            flex-1 px-4 py-3 text-sm font-medium transition-colors
            ${
              activeTab === tab.id
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
            }
          `}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}
