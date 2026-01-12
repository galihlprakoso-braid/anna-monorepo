import 'webextension-polyfill';
import { exampleThemeStorage } from '@extension/storage';

exampleThemeStorage.get().then(theme => {
  console.log('theme', theme);
});

console.log('Background loaded');

// Message types for browser automation
type MessageType =
  | { type: 'CAPTURE_SCREENSHOT' }
  | { type: 'BROWSER_ACTION'; action: 'click' | 'type' | 'scroll' | 'drag'; payload: unknown }
  | { type: 'TOGGLE_DEBUG_GRID'; show: boolean };

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

  return false;
});

async function getActiveTab() {
  // Try lastFocusedWindow first (works better with sidepanel)
  let tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });

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
  console.log('[Agent Content] Document size:', document.documentElement.scrollWidth, 'x', document.documentElement.scrollHeight);
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
        // Get useful info about clicked element
        const tagName = element.tagName.toLowerCase();
        const id = element.id ? `#${element.id}` : '';
        const className = element.className && typeof element.className === 'string' ? `.${element.className.split(' ').join('.')}` : '';
        const text = element.textContent?.trim().slice(0, 30) || '';
        clickedInfo = `${tagName}${id}${className}${text ? ` "${text}"` : ''}`;
        console.log('[Agent Content] Clicked element info:', clickedInfo);
      }

      if (element instanceof HTMLElement) {
        console.log('[Agent Content] Element is HTMLElement, proceeding with click');

        // Focus first if it's focusable
        if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLButtonElement || element instanceof HTMLAnchorElement) {
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
          target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, clientX: x, clientY: y }));
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
        return { action: 'type', details: `Typed "${text.slice(0, 50)}" via keyboard events (no input element focused)` };
      }
    }
    case 'scroll': {
      const { direction, amount = 300 } = payload as { direction: 'up' | 'down' | 'left' | 'right'; amount?: number };
      const scrollMap: Record<string, [number, number]> = {
        up: [0, -amount],
        down: [0, amount],
        left: [-amount, 0],
        right: [amount, 0],
      };
      const [dx, dy] = scrollMap[direction] || [0, 0];
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
    default:
      return { action, details: `Unknown action: ${action}` };
  }
}
