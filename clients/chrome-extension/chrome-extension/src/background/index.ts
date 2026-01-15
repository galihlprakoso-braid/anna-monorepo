import 'webextension-polyfill';
import { exampleThemeStorage, dataSourceStorage, type DataSource } from '@extension/storage';
import { Client } from '@langchain/langgraph-sdk';
import { LANGGRAPH_CONFIG, LOG_PREFIX, AgentExecutionState, GRID_MAX } from './constants';
import type {
  BrowserToolCall,
  BrowserToolResult,
  ScreenshotCapture,
  AgentExecutionContext,
  AgentInitialState,
  InterruptValue,
} from './types';

exampleThemeStorage.get().then(theme => {
  console.log('theme', theme);
});

console.log('Background loaded');

// Auto-open sidepanel when extension icon is clicked
chrome.action.onClicked.addListener(tab => {
  if (tab.id) {
    chrome.sidePanel.open({ tabId: tab.id });
  }
});

// Message types for browser automation
type MessageType =
  | { type: 'CAPTURE_SCREENSHOT' }
  | { type: 'BROWSER_ACTION'; action: 'click' | 'type' | 'scroll' | 'drag'; payload: unknown }
  | { type: 'TOGGLE_DEBUG_GRID'; show: boolean }
  | { type: 'TRIGGER_DATA_COLLECTION'; dataSourceId: string };

// Message handler for sidepanel communication
chrome.runtime.onMessage.addListener((message: MessageType, _sender, sendResponse) => {
  if (message.type === 'CAPTURE_SCREENSHOT') {
    handleScreenshot(sendResponse);
    return true; // Keep channel open for async response
  }

  if (message.type === 'BROWSER_ACTION') {
    handleBrowserAction(message.action, message.payload, sendResponse);
    return true;
  }

  if (message.type === 'TOGGLE_DEBUG_GRID') {
    handleToggleDebugGrid(message.show, sendResponse);
    return true;
  }

  if (message.type === 'TRIGGER_DATA_COLLECTION') {
    handleTriggerDataCollection(message.dataSourceId, sendResponse);
    return true;
  }

  return false;
});

/**
 * Handle manual trigger of data collection from UI
 */
async function handleTriggerDataCollection(dataSourceId: string, sendResponse: (response: unknown) => void) {
  try {
    console.log(`${LOG_PREFIX.BACKGROUND} Manual trigger requested for: ${dataSourceId}`);

    // Validate data source exists before starting
    const dataSource = await getDataSourceById(dataSourceId);
    if (!dataSource) {
      console.error(`${LOG_PREFIX.ERROR} Data source not found: ${dataSourceId}`);
      sendResponse({ success: false, error: 'Data source not found' });
      return;
    }

    if (dataSource.source_type !== 'browser_agent') {
      console.error(`${LOG_PREFIX.ERROR} Not a browser agent data source: ${dataSource.source_type}`);
      sendResponse({ success: false, error: 'Not a browser agent data source' });
      return;
    }

    if (!dataSource.target_url || !dataSource.instruction) {
      console.error(`${LOG_PREFIX.ERROR} Missing required fields: target_url=${!!dataSource.target_url}, instruction=${!!dataSource.instruction}`);
      sendResponse({ success: false, error: 'Missing target_url or instruction' });
      return;
    }

    // Execute collection immediately (don't wait)
    executeDataSourceCollection(dataSourceId)
      .then(() => {
        console.log(`${LOG_PREFIX.BACKGROUND} Manual collection completed for: ${dataSourceId}`);
      })
      .catch(error => {
        console.error(`${LOG_PREFIX.ERROR} Manual collection failed:`, error);
      });

    // Respond immediately to UI
    sendResponse({ success: true, message: 'Data collection started' });
  } catch (error) {
    console.error(`${LOG_PREFIX.ERROR} Error in handleTriggerDataCollection:`, error);
    sendResponse({ success: false, error: String(error) });
  }
}

async function getActiveTab() {
  // Try lastFocusedWindow first (works better with sidepanel)
  const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });

  // Filter out extension pages and find a real webpage
  let tab = tabs.find(t => t.url && !t.url.startsWith('chrome://') && !t.url.startsWith('chrome-extension://'));

  if (!tab) {
    // Fallback: get any active tab from a normal window
    const windows = await chrome.windows.getAll({ windowTypes: ['normal'] });
    for (const win of windows) {
      const winTabs = await chrome.tabs.query({ active: true, windowId: win.id });
      tab = winTabs.find(t => t.url && !t.url.startsWith('chrome://') && !t.url.startsWith('chrome-extension://'));
      if (tab) break;
    }
  }

  return tab;
}

async function handleScreenshot(sendResponse: (response: unknown) => void) {
  try {
    const tab = await getActiveTab();
    if (!tab?.id || !tab.windowId) {
      sendResponse({ success: false, error: 'No active tab found' });
      return;
    }
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });

    // Get viewport dimensions from the tab
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({
        width: window.innerWidth,
        height: window.innerHeight,
      }),
    });
    const viewport = result?.result || { width: 0, height: 0 };

    console.log('[Agent] Screenshot captured, viewport:', viewport);
    sendResponse({ success: true, screenshot: dataUrl, viewport });
  } catch (error) {
    sendResponse({ success: false, error: String(error) });
  }
}

async function handleBrowserAction(action: string, payload: unknown, sendResponse: (response: unknown) => void) {
  console.log('[Agent] handleBrowserAction called:', action, payload);
  try {
    const tab = await getActiveTab();
    console.log('[Agent] Active tab:', tab?.id, tab?.url);
    if (!tab?.id) {
      console.log('[Agent] No active tab found');
      sendResponse({ success: false, error: 'No active tab found' });
      return;
    }

    console.log('[Agent] Executing script in tab:', tab.id);
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: executeBrowserAction,
      args: [action, payload],
    });

    console.log('[Agent] Script execution results:', results);
    const result = results[0]?.result;
    console.log('[Agent] Action result:', result);
    sendResponse({ success: true, details: result });
  } catch (error) {
    console.error('[Agent] Browser action error:', error);
    sendResponse({ success: false, error: String(error) });
  }
}

async function handleToggleDebugGrid(show: boolean, sendResponse: (response: unknown) => void) {
  try {
    const tab = await getActiveTab();
    if (!tab?.id) {
      sendResponse({ success: false, error: 'No active tab found' });
      return;
    }

    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: toggleDebugGrid,
      args: [show],
    });

    sendResponse({ success: true });
  } catch (error) {
    sendResponse({ success: false, error: String(error) });
  }
}

// This function runs in content script context to toggle debug grid
// Shows a 0-100 grid overlay to help visualize grid coordinates
function toggleDebugGrid(show: boolean) {
  const GRID_ID = '__agent_debug_grid__';
  const existing = document.getElementById(GRID_ID);

  if (!show) {
    existing?.remove();
    return;
  }

  if (existing) return; // Already showing

  const grid = document.createElement('div');
  grid.id = GRID_ID;
  grid.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 999999;
  `;

  // Create SVG grid pattern
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '100%');
  svg.style.cssText = 'position: absolute; top: 0; left: 0;';

  const vw = window.innerWidth;
  const vh = window.innerHeight;

  // Draw grid lines at 10% intervals (0, 10, 20, ... 100)
  for (let i = 0; i <= 100; i += 10) {
    const xPixel = (i / 100) * vw;
    const yPixel = (i / 100) * vh;
    const isMajor = i % 50 === 0; // 0, 50, 100 are major lines

    // Vertical line
    const vLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    vLine.setAttribute('x1', String(xPixel));
    vLine.setAttribute('y1', '0');
    vLine.setAttribute('x2', String(xPixel));
    vLine.setAttribute('y2', String(vh));
    vLine.setAttribute('stroke', isMajor ? 'rgba(0,150,0,0.5)' : 'rgba(0,150,0,0.25)');
    vLine.setAttribute('stroke-width', isMajor ? '2' : '1');
    svg.appendChild(vLine);

    // Horizontal line
    const hLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    hLine.setAttribute('x1', '0');
    hLine.setAttribute('y1', String(yPixel));
    hLine.setAttribute('x2', String(vw));
    hLine.setAttribute('y2', String(yPixel));
    hLine.setAttribute('stroke', isMajor ? 'rgba(0,150,0,0.5)' : 'rgba(0,150,0,0.25)');
    hLine.setAttribute('stroke-width', isMajor ? '2' : '1');
    svg.appendChild(hLine);

    // Labels for X axis (top)
    if (i > 0 && i < 100) {
      const xLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      xLabel.setAttribute('x', String(xPixel + 3));
      xLabel.setAttribute('y', '14');
      xLabel.setAttribute('fill', 'rgba(0,100,0,0.9)');
      xLabel.setAttribute('font-size', '12');
      xLabel.setAttribute('font-weight', isMajor ? 'bold' : 'normal');
      xLabel.textContent = String(i);
      svg.appendChild(xLabel);
    }

    // Labels for Y axis (left side)
    if (i > 0 && i < 100) {
      const yLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      yLabel.setAttribute('x', '3');
      yLabel.setAttribute('y', String(yPixel - 3));
      yLabel.setAttribute('fill', 'rgba(0,100,0,0.9)');
      yLabel.setAttribute('font-size', '12');
      yLabel.setAttribute('font-weight', isMajor ? 'bold' : 'normal');
      yLabel.textContent = String(i);
      svg.appendChild(yLabel);
    }
  }

  // Add corner labels
  const corners = [
    { x: 5, y: 14, text: '0,0' },
    { x: vw - 30, y: 14, text: '100,0' },
    { x: 5, y: vh - 5, text: '0,100' },
    { x: vw - 45, y: vh - 5, text: '100,100' },
  ];
  corners.forEach(({ x, y, text }) => {
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', String(x));
    label.setAttribute('y', String(y));
    label.setAttribute('fill', 'rgba(0,100,0,1)');
    label.setAttribute('font-size', '11');
    label.setAttribute('font-weight', 'bold');
    label.textContent = text;
    svg.appendChild(label);
  });

  grid.appendChild(svg);
  document.body.appendChild(grid);
}

// Helper function to show click animation
function showClickAnimation(x: number, y: number) {
  const circle = document.createElement('div');
  circle.style.cssText = `
    position: fixed;
    left: ${x}px;
    top: ${y}px;
    width: 20px;
    height: 20px;
    margin-left: -10px;
    margin-top: -10px;
    border-radius: 50%;
    background: rgba(255, 0, 0, 0.5);
    border: 2px solid red;
    pointer-events: none;
    z-index: 999999;
    animation: clickPulse 0.5s ease-out forwards;
  `;

  // Add animation keyframes if not already added
  if (!document.getElementById('__agent_click_animation_styles__')) {
    const style = document.createElement('style');
    style.id = '__agent_click_animation_styles__';
    style.textContent = `
      @keyframes clickPulse {
        0% {
          transform: scale(1);
          opacity: 1;
        }
        100% {
          transform: scale(3);
          opacity: 0;
        }
      }
    `;
    document.head.appendChild(style);
  }

  document.body.appendChild(circle);
  setTimeout(() => circle.remove(), 500);
}

// This function runs in the content script context (injected into the page)
function executeBrowserAction(action: string, payload: unknown): { action: string; details: string } {
  console.log('[Agent Content] executeBrowserAction called:', action, payload);
  console.log('[Agent Content] Viewport size:', window.innerWidth, 'x', window.innerHeight);
  console.log(
    '[Agent Content] Document size:',
    document.documentElement.scrollWidth,
    'x',
    document.documentElement.scrollHeight,
  );
  console.log('[Agent Content] Scroll position:', window.scrollX, window.scrollY);

  // Helper function to show click animation (must be inside executeBrowserAction for injection)
  function showClickAnimationInline(clickX: number, clickY: number) {
    const circle = document.createElement('div');
    circle.style.cssText = `
      position: fixed;
      left: ${clickX}px;
      top: ${clickY}px;
      width: 20px;
      height: 20px;
      margin-left: -10px;
      margin-top: -10px;
      border-radius: 50%;
      background: rgba(255, 0, 0, 0.5);
      border: 2px solid red;
      pointer-events: none;
      z-index: 999999;
      animation: clickPulse 0.5s ease-out forwards;
    `;

    // Add animation keyframes if not already added
    if (!document.getElementById('__agent_click_animation_styles__')) {
      const style = document.createElement('style');
      style.id = '__agent_click_animation_styles__';
      style.textContent = `
        @keyframes clickPulse {
          0% {
            transform: scale(1);
            opacity: 1;
          }
          100% {
            transform: scale(3);
            opacity: 0;
          }
        }
      `;
      document.head.appendChild(style);
    }

    document.body.appendChild(circle);
    setTimeout(() => circle.remove(), 500);
  }

  switch (action) {
    case 'click': {
      const { x, y } = payload as { x: number; y: number };
      console.log('[Agent Content] Click at coordinates:', x, y);
      console.log('[Agent Content] Is coordinate in viewport?', x <= window.innerWidth && y <= window.innerHeight);

      const element = document.elementFromPoint(x, y);
      console.log('[Agent Content] Element at point:', element);
      console.log('[Agent Content] Element tagName:', element?.tagName);
      console.log('[Agent Content] Element outerHTML (first 200 chars):', element?.outerHTML?.slice(0, 200));

      // Show click animation
      showClickAnimationInline(x, y);

      let clickedInfo = '';
      if (element) {
        // Get comprehensive info about clicked element for better AI feedback
        const tagName = element.tagName.toLowerCase();
        const id = element.id ? `#${element.id}` : '';
        const className =
          element.className && typeof element.className === 'string'
            ? `.${element.className.split(' ').join('.')}`
            : '';

        // Get full text content (not truncated)
        const text = element.textContent?.trim() || '';
        const textPreview = text.length > 50 ? text.slice(0, 50) + '...' : text;

        // Get ARIA labels for better semantic understanding
        const ariaLabel = element.getAttribute('aria-label') || '';
        const ariaRole = element.getAttribute('role') || '';
        const ariaLabelledBy = element.getAttribute('aria-labelledby') || '';

        // Get computed styles for visual description
        const computedStyle = window.getComputedStyle(element);
        const backgroundColor = computedStyle.backgroundColor;
        const color = computedStyle.color;
        const fontSize = computedStyle.fontSize;
        const fontWeight = computedStyle.fontWeight;

        // Detect visual characteristics
        const visualDesc: string[] = [];

        // Color detection - convert rgb to human-readable colors
        const rgbToColorName = (rgb: string): string => {
          if (rgb === 'rgba(0, 0, 0, 0)' || rgb === 'transparent') return 'transparent';
          const match = rgb.match(/\d+/g);
          if (!match) return rgb;
          const [r, g, b] = match.map(Number);

          // Simple color detection
          if (r > 200 && g > 200 && b > 200) return 'white/light';
          if (r < 50 && g < 50 && b < 50) return 'black/dark';
          if (r > 150 && g < 100 && b < 100) return 'red';
          if (r < 100 && g > 150 && b < 100) return 'green';
          if (r < 100 && g < 100 && b > 150) return 'blue';
          if (r > 150 && g > 150 && b < 100) return 'yellow';
          if (r > 150 && g < 100 && b > 150) return 'purple';
          if (r > 150 && g > 100 && b < 100) return 'orange';
          return rgb;
        };

        const bgColorName = rgbToColorName(backgroundColor);
        if (bgColorName !== 'transparent') {
          visualDesc.push(`background: ${bgColorName}`);
        }

        const textColorName = rgbToColorName(color);
        visualDesc.push(`text: ${textColorName}`);

        // Font weight detection
        const weight = parseInt(fontWeight);
        if (weight >= 700) {
          visualDesc.push('bold text');
        }

        // Build rich description
        const parts: string[] = [];

        // 1. Element type with ARIA role if available
        if (ariaRole) {
          parts.push(`${tagName} (role: ${ariaRole})`);
        } else {
          parts.push(tagName);
        }

        // 2. Element identifier (id/class)
        if (id || className) {
          parts.push(`${id}${className}`);
        }

        // 3. Visual characteristics
        if (visualDesc.length > 0) {
          parts.push(`[${visualDesc.join(', ')}]`);
        }

        // 4. ARIA label (semantic meaning)
        if (ariaLabel) {
          parts.push(`aria-label="${ariaLabel}"`);
        }

        // 5. Text content
        if (text) {
          parts.push(`text="${textPreview}"`);
        }

        clickedInfo = parts.join(' | ');
        console.log('[Agent Content] Clicked element info:', clickedInfo);
      }

      if (element instanceof HTMLElement) {
        console.log('[Agent Content] Element is HTMLElement, proceeding with click');

        // Focus first if it's focusable
        if (
          element instanceof HTMLInputElement ||
          element instanceof HTMLTextAreaElement ||
          element instanceof HTMLButtonElement ||
          element instanceof HTMLAnchorElement
        ) {
          console.log('[Agent Content] Focusing element');
          element.focus();
        }

        // Dispatch proper mouse events sequence
        console.log('[Agent Content] Dispatching mousedown');
        element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, clientX: x, clientY: y }));
        console.log('[Agent Content] Dispatching mouseup');
        element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, clientX: x, clientY: y }));
        console.log('[Agent Content] Calling element.click()');
        element.click();
        console.log('[Agent Content] Click completed');

        return { action: 'click', details: `Clicked on ${clickedInfo} at (${x}, ${y})` };
      } else {
        console.log('[Agent Content] Element is NOT HTMLElement, using fallback');
        // Fallback: dispatch click event at coordinates
        const target = document.elementFromPoint(x, y);
        if (target) {
          console.log('[Agent Content] Fallback target:', target);
          target.dispatchEvent(
            new MouseEvent('mousedown', { bubbles: true, cancelable: true, clientX: x, clientY: y }),
          );
          target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, clientX: x, clientY: y }));
          target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, clientX: x, clientY: y }));
          return { action: 'click', details: `Clicked at (${x}, ${y}) on non-HTMLElement` };
        }
        console.log('[Agent Content] No element found at coordinates');
        return { action: 'click', details: `No element found at (${x}, ${y})` };
      }
    }
    case 'type': {
      const { text } = payload as { text: string };
      const activeElement = document.activeElement;
      if (activeElement instanceof HTMLInputElement || activeElement instanceof HTMLTextAreaElement) {
        activeElement.value = text;
        activeElement.dispatchEvent(new Event('input', { bubbles: true }));
        return { action: 'type', details: `Typed "${text.slice(0, 50)}" into ${activeElement.tagName.toLowerCase()}` };
      } else {
        // Try to type using keyboard events
        for (const char of text) {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
          document.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
          document.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
        }
        return {
          action: 'type',
          details: `Typed "${text.slice(0, 50)}" via keyboard events (no input element focused)`,
        };
      }
    }
    case 'scroll': {
      const { direction, amount = 300, x, y } = payload as {
        direction: 'up' | 'down' | 'left' | 'right';
        amount?: number;
        x?: number; // Pixel coordinates (already converted from grid)
        y?: number;
      };

      const scrollMap: Record<string, [number, number]> = {
        up: [0, -amount],
        down: [0, amount],
        left: [-amount, 0],
        right: [amount, 0],
      };
      const [dx, dy] = scrollMap[direction] || [0, 0];

      // If coordinates provided, find and scroll specific element
      if (x !== undefined && y !== undefined) {
        const element = document.elementFromPoint(x, y);
        if (element) {
          // Find closest scrollable parent
          let scrollableElement: Element | null = element;
          while (scrollableElement) {
            const style = window.getComputedStyle(scrollableElement);
            const isScrollable =
              style.overflow === 'auto' ||
              style.overflow === 'scroll' ||
              style.overflowY === 'auto' ||
              style.overflowY === 'scroll' ||
              style.overflowX === 'auto' ||
              style.overflowX === 'scroll';

            if (
              isScrollable &&
              (scrollableElement.scrollHeight > scrollableElement.clientHeight ||
                scrollableElement.scrollWidth > scrollableElement.clientWidth)
            ) {
              scrollableElement.scrollBy(dx, dy);
              return {
                action: 'scroll',
                details: `Scrolled ${direction} by ${amount}px at (${x}, ${y}) on element: ${scrollableElement.tagName}.${scrollableElement.className}`,
              };
            }
            scrollableElement = scrollableElement.parentElement;
          }
          // Fallback if no scrollable parent found
          window.scrollBy(dx, dy);
          return {
            action: 'scroll',
            details: `Scrolled ${direction} by ${amount}px at (${x}, ${y}) - no scrollable element found, scrolled window`,
          };
        }
      }

      // No coordinates, scroll entire window (backward compatible)
      window.scrollBy(dx, dy);
      return { action: 'scroll', details: `Scrolled ${direction} by ${amount}px` };
    }
    case 'drag': {
      const { startX, startY, endX, endY } = payload as {
        startX: number;
        startY: number;
        endX: number;
        endY: number;
      };
      const element = document.elementFromPoint(startX, startY);
      if (element) {
        element.dispatchEvent(new MouseEvent('mousedown', { clientX: startX, clientY: startY, bubbles: true }));
        element.dispatchEvent(new MouseEvent('mousemove', { clientX: endX, clientY: endY, bubbles: true }));
        element.dispatchEvent(new MouseEvent('mouseup', { clientX: endX, clientY: endY, bubbles: true }));
        return { action: 'drag', details: `Dragged from (${startX}, ${startY}) to (${endX}, ${endY})` };
      }
      return { action: 'drag', details: `No element found at start position (${startX}, ${startY})` };
    }
    case 'wait': {
      const { ms } = payload as { ms: number };
      // Wait synchronously in the content script context
      const start = Date.now();
      while (Date.now() - start < ms) {
        // Busy wait (not ideal but works in injected script context)
      }
      return { action: 'wait', details: `Waited ${ms}ms` };
    }
    case 'screenshot': {
      const { reason } = payload as { reason?: string };
      // Screenshot is handled by the background script via captureScreenshotFromTab
      // This action just returns acknowledgment
      return { action: 'screenshot', details: reason ? `Screenshot: ${reason}` : 'Screenshot captured' };
    }
    default:
      return { action, details: `Unknown action: ${action}` };
  }
}

// ============================================================================
// Data Source Scheduling
// ============================================================================

const SYNC_ALARM_NAME = 'syncDataSources';
const SYNC_INTERVAL_MINUTES = 5; // Sync with backend every 5 minutes

/**
 * Get data source by ID - tries cache first, then falls back to API
 */
async function getDataSourceById(id: string): Promise<DataSource | null> {
  // Try cache first
  const cache = await dataSourceStorage.get();
  const cached = cache.dataSources.find(ds => ds.id === id);
  if (cached) {
    console.log(`${LOG_PREFIX.BACKGROUND} Found data source in cache: ${id}`);
    return cached;
  }

  // Fallback to API
  try {
    console.log(`${LOG_PREFIX.BACKGROUND} Data source not in cache, fetching from API: ${id}`);
    const apiUrl = process.env['CEB_API_URL'] || 'http://localhost:8000/api/v1';
    const response = await fetch(`${apiUrl}/data-sources/${id}`);
    if (response.ok) {
      const dataSource = await response.json();
      console.log(`${LOG_PREFIX.BACKGROUND} Fetched data source from API: ${dataSource.name}`);
      return dataSource;
    } else {
      console.error(`${LOG_PREFIX.ERROR} API returned status ${response.status} for data source ${id}`);
    }
  } catch (error) {
    console.error(`${LOG_PREFIX.ERROR} Failed to fetch data source from API:`, error);
  }
  return null;
}

/**
 * Initialize data source scheduling on extension startup
 */
async function initializeDataSourceScheduling() {
  console.log('[Background] Initializing data source scheduling');

  // Create sync alarm to fetch data sources from backend
  chrome.alarms.create(SYNC_ALARM_NAME, {
    periodInMinutes: SYNC_INTERVAL_MINUTES,
    when: Date.now() + 10000, // Start in 10 seconds
  });

  // Initial sync
  await syncDataSources();
}

/**
 * Sync data sources from backend API
 */
async function syncDataSources() {
  try {
    console.log('[Background] Syncing data sources from backend...');

    const apiUrl = process.env['CEB_API_URL'] || 'http://localhost:8000/api/v1';
    const response = await fetch(`${apiUrl}/data-sources?status=active`);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    const dataSources: DataSource[] = data.items || [];

    await dataSourceStorage.set({
      dataSources,
      lastSyncAt: Date.now(),
    });

    console.log(`[Background] Synced ${dataSources.length} active data sources`);

    // Schedule alarms for each active data source
    await scheduleDataSourceAlarms(dataSources);
  } catch (error) {
    console.error('[Background] Failed to sync data sources:', error);
  }
}

/**
 * Create/update alarms for each active data source
 */
async function scheduleDataSourceAlarms(dataSources: DataSource[]) {
  // Clear existing data source alarms
  const alarms = await chrome.alarms.getAll();
  for (const alarm of alarms) {
    if (alarm.name.startsWith('ds_')) {
      await chrome.alarms.clear(alarm.name);
    }
  }

  // Create new alarms
  for (const ds of dataSources) {
    if (ds.status === 'active' && ds.source_type === 'browser_agent') {
      const alarmName = `ds_${ds.id}`;

      chrome.alarms.create(alarmName, {
        periodInMinutes: ds.schedule_interval_minutes,
        when: Date.now() + 30000, // Start in 30 seconds
      });

      console.log(`[Background] Scheduled alarm for "${ds.name}" every ${ds.schedule_interval_minutes}min`);
    }
  }
}

/**
 * Handle alarm fires
 */
chrome.alarms.onAlarm.addListener(async alarm => {
  console.log('[Background] Alarm fired:', alarm.name);

  if (alarm.name === SYNC_ALARM_NAME) {
    await syncDataSources();
  } else if (alarm.name.startsWith('ds_')) {
    const dataSourceId = alarm.name.replace('ds_', '');
    await executeDataSourceCollection(dataSourceId);
  }
});

/**
 * Execute data collection for a data source
 */
async function executeDataSourceCollection(dataSourceId: string) {
  try {
    // Check if execution already running (prevent overlaps from scheduled alarms)
    const activeExecution = activeExecutions.get(dataSourceId);
    if (activeExecution) {
      const runningFor = Math.round((Date.now() - activeExecution.startedAt) / 1000);
      console.log(
        `${LOG_PREFIX.BACKGROUND} Skipping: execution already running for "${dataSourceId}" ` +
          `(thread: ${activeExecution.threadId}, running for ${runningFor}s)`,
      );
      return;
    }

    console.log(`${LOG_PREFIX.BACKGROUND} Executing data collection for: ${dataSourceId}`);

    // Get data source - try cache first, then API
    const dataSource = await getDataSourceById(dataSourceId);

    if (!dataSource) {
      console.error(`${LOG_PREFIX.ERROR} Data source not found: ${dataSourceId}`);
      return;
    }

    if (dataSource.source_type !== 'browser_agent') {
      console.log(`${LOG_PREFIX.BACKGROUND} Skipping non-browser-agent source: ${dataSource.name}`);
      return;
    }

    // Ensure dedicated tab exists and is ready
    const tabId = await ensureDedicatedTab(dataSourceId, dataSource.target_url!);

    console.log(`${LOG_PREFIX.BACKGROUND} Using dedicated tab ${tabId} for data collection`);

    // Mark execution as active BEFORE starting (threadId will be updated when created)
    activeExecutions.set(dataSourceId, {
      threadId: 'pending',
      startedAt: Date.now(),
      tabId,
    });

    try {
      // Execute browser agent in background
      await executeBrowserAgentInBackground(dataSourceId, tabId, dataSource.instruction!);

      console.log(`${LOG_PREFIX.BACKGROUND} Data collection completed for: ${dataSource.name}`);
    } finally {
      // Clear execution tracking when done (success or error)
      activeExecutions.delete(dataSourceId);
      console.log(`${LOG_PREFIX.BACKGROUND} Cleared execution tracking for: ${dataSourceId}`);
    }
  } catch (error) {
    console.error(`${LOG_PREFIX.ERROR} Data collection failed:`, error);
    // Ensure cleanup on error
    activeExecutions.delete(dataSourceId);
  }
}

// ============================================================================
// Dedicated Tab Management
// ============================================================================

/**
 * Tab registry to track dedicated tabs for each data source
 * Key: dataSourceId, Value: tabId
 */
const dataSourceTabs = new Map<string, number>();

/**
 * Track active executions to prevent overlapping scheduled tasks
 * Key: dataSourceId, Value: execution info
 */
const activeExecutions = new Map<
  string,
  {
    threadId: string;
    startedAt: number;
    tabId: number;
  }
>();

/**
 * Ensure dedicated tab exists for a data source
 * If tab already exists and is valid, reuse it. Otherwise create new.
 */
async function ensureDedicatedTab(dataSourceId: string, targetUrl: string): Promise<number> {
  const existingTabId = dataSourceTabs.get(dataSourceId);

  // Check if existing tab is still valid
  if (existingTabId !== undefined) {
    try {
      const tab = await chrome.tabs.get(existingTabId);
      const targetOrigin = new URL(targetUrl).origin;

      if (tab && tab.url?.startsWith(targetOrigin)) {
        console.log(`${LOG_PREFIX.TAB} Reusing existing tab ${existingTabId} for data source ${dataSourceId}`);
        // Reload to ensure fresh state
        await chrome.tabs.reload(existingTabId);
        await waitForTabLoad(existingTabId);
        return existingTabId;
      }
    } catch (error) {
      // Tab no longer exists, remove from registry
      console.log(`${LOG_PREFIX.TAB} Tab ${existingTabId} no longer exists, creating new one`);
      dataSourceTabs.delete(dataSourceId);
    }
  }

  // Create new dedicated tab
  console.log(`${LOG_PREFIX.TAB} Creating new dedicated tab for data source ${dataSourceId}`);

  const tab = await chrome.tabs.create({
    url: targetUrl,
    active: false, // Silent background execution
  });

  if (!tab.id) {
    throw new Error(`${LOG_PREFIX.ERROR} Failed to create tab`);
  }

  // Register the tab
  dataSourceTabs.set(dataSourceId, tab.id);

  // Wait for page to load
  await waitForTabLoad(tab.id);

  return tab.id;
}

/**
 * Wait for tab to finish loading
 */
async function waitForTabLoad(tabId: number): Promise<void> {
  const startTime = Date.now();

  while (Date.now() - startTime < LANGGRAPH_CONFIG.TAB_LOAD_TIMEOUT_MS) {
    try {
      const tab = await chrome.tabs.get(tabId);
      if (tab.status === 'complete') {
        // Extra buffer after load complete
        await new Promise(resolve => setTimeout(resolve, LANGGRAPH_CONFIG.TAB_LOAD_BUFFER_MS));
        return;
      }
    } catch (error) {
      throw new Error(`${LOG_PREFIX.ERROR} Tab ${tabId} no longer exists`);
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  throw new Error(`${LOG_PREFIX.ERROR} Tab ${tabId} load timeout`);
}

/**
 * Close dedicated tab for a data source
 * Call this when data source is deleted or deactivated
 */
export async function closeDedicatedTab(dataSourceId: string): Promise<void> {
  const tabId = dataSourceTabs.get(dataSourceId);
  if (tabId !== undefined) {
    try {
      await chrome.tabs.remove(tabId);
      console.log(`${LOG_PREFIX.TAB} Closed dedicated tab ${tabId} for data source ${dataSourceId}`);
    } catch (error) {
      console.warn(`${LOG_PREFIX.TAB} Failed to close tab ${tabId}:`, error);
    } finally {
      dataSourceTabs.delete(dataSourceId);
      activeExecutions.delete(dataSourceId); // Also clear execution tracking
    }
  }
}

// ============================================================================
// Screenshot and Tool Execution Helpers
// ============================================================================

/**
 * Capture screenshot from specific tab
 */
async function captureScreenshotFromTab(tabId: number): Promise<ScreenshotCapture | null> {
  try {
    const tab = await chrome.tabs.get(tabId);

    if (!tab.windowId) {
      throw new Error(`${LOG_PREFIX.ERROR} Tab ${tabId} has no window`);
    }

    // Ensure tab is active in its window (required for captureVisibleTab)
    await chrome.tabs.update(tabId, { active: true });
    await new Promise(resolve => setTimeout(resolve, LANGGRAPH_CONFIG.TAB_ACTIVATION_DELAY_MS));

    // Capture screenshot
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });

    // Get viewport dimensions
    const [result] = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => ({
        width: window.innerWidth,
        height: window.innerHeight,
      }),
    });

    return {
      screenshot: dataUrl,
      viewport: result?.result || { width: 800, height: 600 },
    };
  } catch (error) {
    console.error(`${LOG_PREFIX.SCREENSHOT} Screenshot capture failed:`, error);
    return null;
  }
}

/**
 * Execute tool call on specific tab
 * Converts grid coordinates and dispatches to executeBrowserAction
 */
async function executeToolCallOnTab(tabId: number, action: string, args: Record<string, unknown>): Promise<string> {
  try {
    console.log(`${LOG_PREFIX.TOOL} Executing ${action} on tab ${tabId} with args:`, args);

    // Convert grid coordinates to pixels for click/drag/scroll actions
    let processedArgs = args;

    if (action === 'click' && 'x' in args && 'y' in args) {
      const capture = await captureScreenshotFromTab(tabId);
      const viewport = capture?.viewport || { width: 800, height: 600 };

      processedArgs = {
        x: Math.round(((args.x as number) / GRID_MAX) * viewport.width),
        y: Math.round(((args.y as number) / GRID_MAX) * viewport.height),
      };
    } else if (action === 'drag' && 'start_x' in args) {
      const capture = await captureScreenshotFromTab(tabId);
      const viewport = capture?.viewport || { width: 800, height: 600 };

      processedArgs = {
        startX: Math.round(((args.start_x as number) / GRID_MAX) * viewport.width),
        startY: Math.round(((args.start_y as number) / GRID_MAX) * viewport.height),
        endX: Math.round(((args.end_x as number) / GRID_MAX) * viewport.width),
        endY: Math.round(((args.end_y as number) / GRID_MAX) * viewport.height),
      };
    } else if (action === 'scroll' && 'x' in args && 'y' in args && args.x !== null && args.y !== null) {
      const capture = await captureScreenshotFromTab(tabId);
      const viewport = capture?.viewport || { width: 800, height: 600 };

      processedArgs = {
        ...args,
        x: Math.round(((args.x as number) / GRID_MAX) * viewport.width),
        y: Math.round(((args.y as number) / GRID_MAX) * viewport.height),
      };
    }

    // Execute using existing executeBrowserAction function
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: executeBrowserAction, // Existing function
      args: [action, processedArgs],
    });

    const result = results[0]?.result;
    const details = result?.details || `${action} executed`;
    console.log(`${LOG_PREFIX.TOOL} Tool result: ${details}`);
    return details;
  } catch (error) {
    console.error(`${LOG_PREFIX.TOOL} Tool execution failed:`, error);
    return `Error: ${error instanceof Error ? error.message : String(error)}`;
  }
}

// ============================================================================
// LangGraph Client Integration
// ============================================================================

/**
 * Execute browser agent in background with full LangGraph integration
 * Mirrors useBrowserAgent hook but for background context
 */
async function executeBrowserAgentInBackground(
  dataSourceId: string,
  tabId: number,
  instruction: string,
): Promise<void> {
  console.log(`${LOG_PREFIX.AGENT} Starting execution for data source: ${dataSourceId}`);
  console.log(`${LOG_PREFIX.AGENT} Tab: ${tabId}`);
  console.log(`${LOG_PREFIX.AGENT} Instruction: ${instruction}`);

  try {
    // Step 1: Capture initial screenshot
    const initialCapture = await captureScreenshotFromTab(tabId);
    if (!initialCapture) {
      throw new Error(`${LOG_PREFIX.ERROR} Failed to capture initial screenshot`);
    }

    console.log(`${LOG_PREFIX.AGENT} Initial screenshot captured`);

    // Step 2: Create LangGraph client
    const client = new Client({ apiUrl: LANGGRAPH_CONFIG.API_URL });

    // Step 3: Create thread for this execution
    const thread = await client.threads.create();
    const threadId = thread.thread_id;

    console.log(`${LOG_PREFIX.AGENT} Created thread: ${threadId}`);

    // Update activeExecutions with actual threadId
    const executionInfo = activeExecutions.get(dataSourceId);
    if (executionInfo) {
      executionInfo.threadId = threadId;
    }

    // Step 4: Prepare initial state
    const initialState: AgentInitialState = {
      messages: [
        {
          type: 'human',
          content: [
            { type: 'text', text: instruction },
            { type: 'image_url', image_url: { url: initialCapture.screenshot } },
          ],
        },
      ],
      current_screenshot: initialCapture.screenshot,
      viewport: initialCapture.viewport,
    };

    // Step 5: Create execution context
    const context: AgentExecutionContext = {
      dataSourceId,
      tabId,
      threadId,
      state: AgentExecutionState.RUNNING,
      iterationCount: 0,
    };

    // Step 6: Run interrupt/resume loop
    await runAgentInterruptLoop(client, context, initialState);

    console.log(`${LOG_PREFIX.AGENT} Execution completed successfully`);
  } catch (error) {
    console.error(`${LOG_PREFIX.ERROR} Agent execution failed:`, error);
    throw error;
  }
}

/**
 * Main agent interrupt/resume loop
 * Implements the pattern from LangGraph SDK's useStream hook
 *
 * Key insights from SDK analysis (see @langchain/langgraph-sdk/dist/ui/manager.js):
 * 1. Stream yields { event, data } chunks where event is 'values', 'error', etc.
 * 2. Don't break early on interrupt - process ALL stream events
 * 3. After stream ends, check final values for __interrupt__
 * 4. Resume with { command: { resume: ... } } structure
 */
const runAgentInterruptLoop = async (
  client: Client,
  context: AgentExecutionContext,
  initialState: AgentInitialState | null,
): Promise<void> => {
  // Initial input for first iteration, undefined for subsequent resumes
  let currentInput: AgentInitialState | null | undefined = initialState;
  // Resume command for subsequent iterations after interrupt
  let resumeCommand: { resume: BrowserToolResult } | undefined = undefined;

  while (context.iterationCount < LANGGRAPH_CONFIG.MAX_ITERATIONS) {
    context.iterationCount++;
    const isResume = !!resumeCommand;
    console.log(`${LOG_PREFIX.AGENT} ========== Iteration ${context.iterationCount} ==========`);
    console.log(`${LOG_PREFIX.AGENT} Mode: ${isResume ? 'RESUME' : 'INITIAL'}`);
    if (isResume) {
      console.log(`${LOG_PREFIX.AGENT} Resume command:`, JSON.stringify(resumeCommand).substring(0, 200));
    }

    try {
      // Ensure threadId is valid
      if (!context.threadId) {
        throw new Error(`${LOG_PREFIX.ERROR} No thread ID available`);
      }

      console.log(`${LOG_PREFIX.AGENT} Thread ID: ${context.threadId}`);

      // Build stream options based on whether we're resuming or starting fresh
      // This mirrors how the SDK's submit() function works
      const stream = resumeCommand
        ? client.runs.stream(context.threadId, LANGGRAPH_CONFIG.ASSISTANT_ID, {
            input: undefined, // Explicitly undefined when resuming
            command: resumeCommand,
            streamMode: 'values' as const,
          })
        : client.runs.stream(context.threadId, LANGGRAPH_CONFIG.ASSISTANT_ID, {
            input: currentInput,
            streamMode: 'values' as const,
          });

      // Track latest values from stream (don't break early!)
      // This is how the SDK's StreamManager.enqueue() works
      let latestValues: Record<string, unknown> | null = null;
      let chunkCount = 0;

      // Process ALL stream events (SDK pattern: never break early)
      for await (const chunk of stream) {
        chunkCount++;
        const chunkEvent = (chunk as { event?: string }).event;
        const chunkData = (chunk as { data?: unknown }).data;

        // Detailed logging for debugging
        console.log(`${LOG_PREFIX.AGENT} Chunk #${chunkCount}:`, {
          event: chunkEvent,
          hasData: !!chunkData,
          dataKeys: chunkData && typeof chunkData === 'object' ? Object.keys(chunkData as object) : [],
        });

        // Handle error events
        if (chunkEvent === 'error') {
          throw new Error(`Stream error: ${JSON.stringify(chunkData)}`);
        }

        // Store latest values when we get a 'values' event
        // The SDK does: if (event === "values") this.setStreamValues(data)
        if (chunkEvent === 'values' && chunkData && typeof chunkData === 'object') {
          latestValues = chunkData as Record<string, unknown>;
          const hasInterrupt = '__interrupt__' in latestValues;
          console.log(`${LOG_PREFIX.AGENT} Values event - keys:`, Object.keys(latestValues), 'hasInterrupt:', hasInterrupt);

          // Log if interrupt detected (but don't break!)
          if (hasInterrupt) {
            console.log(`${LOG_PREFIX.INTERRUPT} Detected! Value:`, JSON.stringify(latestValues.__interrupt__).substring(0, 300));
          }
        }
      }

      console.log(`${LOG_PREFIX.AGENT} Stream ended after ${chunkCount} chunks`);
      console.log(`${LOG_PREFIX.AGENT} Final latestValues keys:`, latestValues ? Object.keys(latestValues) : 'null');

      // After stream ends, check final values for interrupt
      // This mirrors the SDK's interrupt getter logic
      if (latestValues && '__interrupt__' in latestValues) {
        const interruptArray = latestValues.__interrupt__;
        console.log(`${LOG_PREFIX.INTERRUPT} Found __interrupt__, isArray:`, Array.isArray(interruptArray));

        if (Array.isArray(interruptArray) && interruptArray.length > 0) {
          console.log(`${LOG_PREFIX.INTERRUPT} Processing ${interruptArray.length} interrupt(s)`);

          // Process interrupt
          context.state = AgentExecutionState.INTERRUPTED;
          const resumeValue = await handleInterrupt(context, interruptArray);

          console.log(`${LOG_PREFIX.INTERRUPT} Got resume value, preparing for next iteration`);
          console.log(`${LOG_PREFIX.INTERRUPT} Resume value:`, JSON.stringify(resumeValue).substring(0, 200));

          // Set up for next iteration with resume command
          // Clear input and set resume command (matches SDK pattern)
          currentInput = undefined;
          resumeCommand = { resume: resumeValue };
        } else {
          console.log(`${LOG_PREFIX.AGENT} __interrupt__ is empty or not array, treating as complete`);
          context.state = AgentExecutionState.COMPLETED;
          return;
        }
      } else {
        // No interrupt in final values = execution complete
        console.log(`${LOG_PREFIX.AGENT} No __interrupt__ in final values, execution finished`);
        if (latestValues) {
          console.log(`${LOG_PREFIX.AGENT} Final state keys:`, Object.keys(latestValues));
        }
        context.state = AgentExecutionState.COMPLETED;
        return;
      }
    } catch (error) {
      console.error(`${LOG_PREFIX.ERROR} Error in iteration ${context.iterationCount}:`, error);
      context.state = AgentExecutionState.FAILED;
      throw error;
    }
  }

  console.warn(`${LOG_PREFIX.AGENT} Max iterations (${LANGGRAPH_CONFIG.MAX_ITERATIONS}) reached`);
  context.state = AgentExecutionState.FAILED;
};

/**
 * Handle interrupt by executing tool call
 */
const handleInterrupt = async (context: AgentExecutionContext, interruptData: unknown): Promise<BrowserToolResult> => {
  console.log(`${LOG_PREFIX.INTERRUPT} Processing interrupt...`);

  // Extract tool call from interrupt value
  const toolCall = extractToolCallFromInterrupt(interruptData);

  if (!toolCall) {
    throw new Error(`${LOG_PREFIX.ERROR} Invalid interrupt: no tool call found`);
  }

  console.log(`${LOG_PREFIX.INTERRUPT} Tool call:`, toolCall);

  // Execute tool on the dedicated tab
  const result = await executeToolCallOnTab(context.tabId, toolCall.action, toolCall.args);

  console.log(`${LOG_PREFIX.INTERRUPT} Tool result:`, result);

  // Capture screenshot if requested
  let screenshot: string | null = null;
  let viewport: { width: number; height: number } | null = null;

  if (toolCall.request_screenshot) {
    const capture = await captureScreenshotFromTab(context.tabId);
    if (capture) {
      screenshot = capture.screenshot;
      viewport = capture.viewport;
      console.log(`${LOG_PREFIX.INTERRUPT} Post-action screenshot captured`);
    }
  }

  return {
    result,
    screenshot,
    viewport,
  };
};

/**
 * Extract BrowserToolCall from interrupt value
 */
const extractToolCallFromInterrupt = (interruptData: unknown): BrowserToolCall | null => {
  try {
    // The interrupt value structure from browser_agent tool_node.py
    // should be an array: [{ value: { action, args, request_screenshot } }]
    if (Array.isArray(interruptData) && interruptData.length > 0) {
      const firstInterrupt = interruptData[0] as InterruptValue;
      if (firstInterrupt && 'value' in firstInterrupt) {
        const value = firstInterrupt.value;
        if ('action' in value && 'args' in value) {
          return {
            action: value.action,
            args: value.args || {},
            request_screenshot: value.request_screenshot || false,
          };
        }
      }
    }
    return null;
  } catch (error) {
    console.error(`${LOG_PREFIX.ERROR} Failed to extract tool call:`, error);
    return null;
  }
};

// Initialize on extension install/startup
chrome.runtime.onInstalled.addListener(() => {
  console.log('[Background] Extension installed/updated');
  initializeDataSourceScheduling();
});

chrome.runtime.onStartup.addListener(() => {
  console.log('[Background] Extension started');
  initializeDataSourceScheduling();
});
