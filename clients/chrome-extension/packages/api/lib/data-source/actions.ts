/**
 * Data Source actions (non-API operations)
 */

/**
 * Trigger manual data collection for a browser agent data source
 * Sends message to background script to execute collection immediately
 */
export async function triggerDataCollection(dataSourceId: string): Promise<{
  success: boolean;
  message?: string;
  error?: string;
}> {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(
      {
        type: 'TRIGGER_DATA_COLLECTION',
        dataSourceId,
      },
      (response) => {
        if (chrome.runtime.lastError) {
          resolve({
            success: false,
            error: chrome.runtime.lastError.message,
          });
        } else {
          resolve(response as { success: boolean; message?: string; error?: string });
        }
      }
    );
  });
}
