import type { ScreenshotResponse, BrowserActionResponse, ToggleGridResponse } from '../types/index.js';

export interface Viewport {
  width: number;
  height: number;
}

export interface ScreenshotResult {
  screenshot: string;
  viewport: Viewport;
}

/**
 * Convert 0-100 grid coordinate to pixel coordinate
 */
export function gridToPixel(gridX: number, gridY: number, viewport: Viewport): { x: number; y: number } {
  return {
    x: Math.round((gridX / 100) * viewport.width),
    y: Math.round((gridY / 100) * viewport.height),
  };
}

/**
 * Capture screenshot from the active tab
 */
export async function captureScreenshot(): Promise<ScreenshotResult | null> {
  return new Promise(resolve => {
    chrome.runtime.sendMessage({ type: 'CAPTURE_SCREENSHOT' }, (response: ScreenshotResponse) => {
      if (response?.success && response.screenshot) {
        const viewport = response.viewport || { width: 800, height: 600 };
        resolve({
          screenshot: response.screenshot,
          viewport,
        });
      } else {
        console.error('Screenshot failed:', response?.error);
        resolve(null);
      }
    });
  });
}

/**
 * Execute a browser action via Chrome messaging
 */
export async function executeBrowserAction(action: string, payload: Record<string, unknown>): Promise<string> {
  return new Promise(resolve => {
    chrome.runtime.sendMessage({ type: 'BROWSER_ACTION', action, payload }, (response: BrowserActionResponse) => {
      if (response?.success) {
        resolve(response.details?.details || `${action} executed successfully`);
      } else {
        resolve(`${action} failed: ${response?.error || 'Unknown error'}`);
      }
    });
  });
}

/**
 * Toggle debug grid overlay
 */
export async function toggleDebugGrid(show: boolean): Promise<boolean> {
  return new Promise(resolve => {
    chrome.runtime.sendMessage({ type: 'TOGGLE_DEBUG_GRID', show }, (response: ToggleGridResponse) => {
      resolve(response?.success ?? false);
    });
  });
}
