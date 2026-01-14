import '@src/SidePanel.css';
import { useState } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { withErrorBoundary, withSuspense } from '@extension/shared';
import { ErrorDisplay, LoadingSpinner } from '@extension/ui';
import { queryClient } from '@extension/api';
import { TabNavigation, type TabId } from './components/shared/TabNavigation';
import { ChatUI } from './components/ChatUI';
import { DataSourcesTab } from './components/DataSourcesTab';

const SidePanel = () => {
  const [activeTab, setActiveTab] = useState<TabId>('chat');

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex flex-col h-screen">
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="flex-1 overflow-hidden">
          {activeTab === 'chat' && <ChatUI />}
          {activeTab === 'data-sources' && <DataSourcesTab />}
        </div>
      </div>
    </QueryClientProvider>
  );
};

export default withErrorBoundary(withSuspense(SidePanel, <LoadingSpinner />), ErrorDisplay);
