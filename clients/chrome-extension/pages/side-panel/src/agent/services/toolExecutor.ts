/**
 * Tool executor service for browser automation.
 * Handles execution of browser actions received from LangGraph server interrupts.
 */

import type { BrowserAction, BrowserToolArgs, ClickArgs, TypeArgs, ScrollArgs, DragArgs, WaitArgs } from './serverTypes';
import { executeBrowserAction, captureScreenshot, gridToPixel } from './chromeMessaging';

/**
 * Type guards for runtime type checking
 */
function isClickArgs(args: BrowserToolArgs): args is ClickArgs {
  return 'x' in args && 'y' in args && typeof args.x === 'number' && typeof args.y === 'number';
}

function isTypeArgs(args: BrowserToolArgs): args is TypeArgs {
  return 'text' in args && typeof args.text === 'string';
}

function isScrollArgs(args: BrowserToolArgs): args is ScrollArgs {
  return (
    'direction' in args &&
    'amount' in args &&
    typeof args.direction === 'string' &&
    typeof args.amount === 'number'
  );
}

function isDragArgs(args: BrowserToolArgs): args is DragArgs {
  return (
    'start_x' in args &&
    'start_y' in args &&
    'end_x' in args &&
    'end_y' in args &&
    typeof args.start_x === 'number' &&
    typeof args.start_y === 'number' &&
    typeof args.end_x === 'number' &&
    typeof args.end_y === 'number'
  );
}

function isWaitArgs(args: BrowserToolArgs): args is WaitArgs {
  return 'ms' in args && typeof args.ms === 'number';
}

/**
 * Execute click action, converting grid coordinates to pixels
 */
async function executeClick(args: ClickArgs): Promise<string> {
  const screenshotResult = await captureScreenshot();
  const viewport = screenshotResult?.viewport ?? { width: 800, height: 600 };
  const pixel = gridToPixel(args.x, args.y, viewport);

  console.log('[toolExecutor] Click at grid:', args, '-> pixel:', pixel);

  return executeBrowserAction('click', { x: pixel.x, y: pixel.y });
}

/**
 * Execute type action
 */
async function executeType(args: TypeArgs): Promise<string> {
  console.log('[toolExecutor] Type text:', args.text);
  return executeBrowserAction('type', { text: args.text });
}

/**
 * Execute scroll action
 */
async function executeScroll(args: ScrollArgs): Promise<string> {
  console.log('[toolExecutor] Scroll:', args.direction, args.amount);
  return executeBrowserAction('scroll', {
    direction: args.direction,
    amount: args.amount,
  });
}

/**
 * Execute drag action, converting grid coordinates to pixels
 */
async function executeDrag(args: DragArgs): Promise<string> {
  const screenshotResult = await captureScreenshot();
  const viewport = screenshotResult?.viewport ?? { width: 800, height: 600 };

  const startPixel = gridToPixel(args.start_x, args.start_y, viewport);
  const endPixel = gridToPixel(args.end_x, args.end_y, viewport);

  console.log('[toolExecutor] Drag from:', startPixel, 'to:', endPixel);

  return executeBrowserAction('drag', {
    startX: startPixel.x,
    startY: startPixel.y,
    endX: endPixel.x,
    endY: endPixel.y,
  });
}

/**
 * Execute wait action
 */
async function executeWait(args: WaitArgs): Promise<string> {
  console.log('[toolExecutor] Waiting:', args.ms, 'ms');
  await new Promise(resolve => setTimeout(resolve, args.ms));
  return `Waited ${args.ms}ms`;
}

/**
 * Execute browser action based on action type and arguments.
 * Uses exhaustive type checking with never type for compile-time safety.
 *
 * @param action - The browser action to execute
 * @param args - The arguments for the action
 * @param requestScreenshot - Whether to capture a screenshot after execution (handled by caller)
 * @returns Promise resolving to the result message
 */
export async function executeToolCall(
  action: BrowserAction,
  args: BrowserToolArgs,
  _requestScreenshot: boolean
): Promise<string> {
  // _requestScreenshot is handled by the caller (useBrowserAgent hook)
  // This function just executes the action and returns the result

  switch (action) {
    case 'click': {
      if (!isClickArgs(args)) {
        throw new Error('Invalid click arguments');
      }
      return executeClick(args);
    }

    case 'type': {
      if (!isTypeArgs(args)) {
        throw new Error('Invalid type arguments');
      }
      return executeType(args);
    }

    case 'scroll': {
      if (!isScrollArgs(args)) {
        throw new Error('Invalid scroll arguments');
      }
      return executeScroll(args);
    }

    case 'drag': {
      if (!isDragArgs(args)) {
        throw new Error('Invalid drag arguments');
      }
      return executeDrag(args);
    }

    case 'wait': {
      if (!isWaitArgs(args)) {
        throw new Error('Invalid wait arguments');
      }
      return executeWait(args);
    }

    case 'screenshot': {
      // Screenshot action just returns acknowledgment
      // Actual screenshot is captured by the caller
      return 'Screenshot requested';
    }

    default: {
      // Exhaustive check - TypeScript will error if a case is missed
      const _exhaustive: never = action;
      throw new Error(`Unknown action: ${_exhaustive}`);
    }
  }
}
