import React, { useState } from 'react';
import {
  useDataSources,
  useDataSourceTemplates,
  useCreateFromTemplate,
  useToggleDataSource,
  useDeleteDataSource,
  triggerDataCollection,
  type DataSource,
  DataSourceStatus,
} from '@extension/api';

export function DataSourcesTab() {
  const [showTemplates, setShowTemplates] = useState(false);

  const { data: dataSources, isLoading, error } = useDataSources();
  const { data: templates } = useDataSourceTemplates();
  const createFromTemplate = useCreateFromTemplate();
  const toggleDataSource = useToggleDataSource();
  const deleteDataSource = useDeleteDataSource();

  const handleAddFromTemplate = (templateId: string) => {
    createFromTemplate.mutate(templateId, {
      onSuccess: () => setShowTemplates(false),
    });
  };

  const handleToggle = (id: string) => {
    toggleDataSource.mutate(id);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this data source?')) {
      deleteDataSource.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">Loading data sources...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-red-500">Error loading data sources: {error.message}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="p-4 bg-white border-b">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold">Data Sources</h2>
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600">
            {showTemplates ? 'Hide Templates' : 'Add New'}
          </button>
        </div>
        <p className="text-sm text-gray-600">Manage your data collection sources</p>
      </div>

      {/* Templates Panel */}
      {showTemplates && (
        <div className="p-4 bg-blue-50 border-b">
          <h3 className="font-medium mb-3">Choose a Template</h3>
          <div className="space-y-2">
            {templates?.templates.map(template => (
              <div
                key={template.id}
                className="p-3 bg-white rounded border hover:border-blue-300 cursor-pointer"
                onClick={() => handleAddFromTemplate(template.id)}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium">{template.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                    <div className="flex gap-2 mt-2">
                      <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                        {template.source_type}
                      </span>
                      <span className="text-xs px-2 py-1 bg-blue-100 rounded">
                        Every {template.schedule_interval_minutes}min
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Sources List */}
      <div className="flex-1 overflow-y-auto p-4">
        {dataSources?.items.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">No data sources configured</p>
            <p className="text-sm text-gray-400 mt-2">Click "Add New" to get started</p>
          </div>
        ) : (
          <div className="space-y-3">
            {dataSources?.items.map(ds => (
              <DataSourceCard
                key={ds.id}
                dataSource={ds}
                onToggle={() => handleToggle(ds.id)}
                onDelete={() => handleDelete(ds.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface DataSourceCardProps {
  dataSource: DataSource;
  onToggle: () => void;
  onDelete: () => void;
}

function DataSourceCard({ dataSource, onToggle, onDelete }: DataSourceCardProps) {
  const [isTriggering, setIsTriggering] = useState(false);
  const isActive = dataSource.status === DataSourceStatus.ACTIVE;
  const isOAuth = dataSource.source_type === 'oauth';
  const isBrowserAgent = dataSource.source_type === 'browser_agent';

  const handleTrigger = async () => {
    setIsTriggering(true);
    try {
      const result = await triggerDataCollection(dataSource.id);
      if (result.success) {
        console.log('Data collection triggered:', result.message);
      } else {
        console.error('Failed to trigger collection:', result.error);
      }
    } catch (error) {
      console.error('Error triggering collection:', error);
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg border shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-medium">{dataSource.name}</h3>
          {dataSource.description && (
            <p className="text-sm text-gray-600 mt-1">{dataSource.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          {isBrowserAgent && (
            <button
              onClick={handleTrigger}
              disabled={isTriggering}
              className={`
                p-1.5 rounded transition-colors
                ${
                  isTriggering
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                }
              `}
              title="Trigger collection now">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          )}
          <button
            onClick={onToggle}
            className={`
              px-3 py-1 text-sm rounded transition-colors
              ${
                isActive
                  ? 'bg-green-100 text-green-700 hover:bg-green-200'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }
            `}>
            {isActive ? 'Active' : 'Paused'}
          </button>
          <button
            onClick={onDelete}
            className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200">
            Delete
          </button>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-2 text-sm">
        {isOAuth && dataSource.oauth_provider && (
          <div className="flex items-center gap-2 text-gray-600">
            <span className="font-medium">Provider:</span>
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
              {dataSource.oauth_provider}
            </span>
            <span className="text-yellow-600">(Coming Soon)</span>
          </div>
        )}

        {!isOAuth && dataSource.target_url && (
          <div className="text-gray-600">
            <span className="font-medium">Target:</span>{' '}
            <a
              href={dataSource.target_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline">
              {dataSource.target_url}
            </a>
          </div>
        )}

        <div className="flex items-center gap-4 text-gray-600">
          <div>
            <span className="font-medium">Schedule:</span> Every{' '}
            {dataSource.schedule_interval_minutes} minutes
          </div>
          <div>
            <span className="font-medium">Runs:</span> {dataSource.run_count} (
            {dataSource.success_count} success, {dataSource.error_count} errors)
          </div>
        </div>

        {dataSource.last_run_at && (
          <div className="text-gray-600">
            <span className="font-medium">Last run:</span>{' '}
            {new Date(dataSource.last_run_at).toLocaleString()}
          </div>
        )}

        {dataSource.last_error && (
          <div className="p-2 bg-red-50 text-red-700 rounded text-xs">
            <span className="font-medium">Error:</span> {dataSource.last_error}
          </div>
        )}
      </div>
    </div>
  );
}
