# Technical Plan: Chrome Extension Browser Agent with LangChain

## Executive Summary

A Chrome Extension with a LangChain agent that executes dynamic SKILLs (markdown prompt files). Simple UI: skill list in side panel, click to execute, output displayed. Uses LangChain v1 `createAgent` with built-in `summarizationMiddleware`. Comprehensive evaluation with LangSmith/Vitest integration.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Chrome Extension                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                     Side Panel (React UI)                        ││
│  │  ┌───────────────┐          ┌──────────────────────────────────┐││
│  │  │  Skill List   │ ────────▶│      Output Display              │││
│  │  │  (click)      │          │      (scraped data)              │││
│  │  └───────────────┘          └──────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
│                          │                                           │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                  Background Service Worker                       ││
│  │  ┌─────────────────────────────────────────────────────────────┐││
│  │  │                      LLM Module                             │││
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐│││
│  │  │  │ createAgent  │  │ summarization│  │  Browser Tools     ││││
│  │  │  │ (langchain)  │  │ Middleware   │  │  (ARIA + Natural)  ││││
│  │  │  └──────────────┘  └──────────────┘  └────────────────────┘│││
│  │  └─────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
│                          │                                           │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                     Content Script (injected)                    ││
│  │  ┌──────────────────────────────────────────────────────────┐   ││
│  │  │  DOM Walker + Shadow DOM + dispatchEvent for actions     │   ││
│  │  └──────────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. User clicks a SKILL in side panel
2. Background worker loads SKILL prompt from `.prompt.md` file
3. `createAgent` executes with skill prompt injected via `dynamicSystemPromptMiddleware`
4. Agent calls `snapshot` tool → message to content script → DOM walk → YAML with refs
5. Agent sees refs, decides action: `click ref="ref_3"`
6. Tool sends action to content script → `element.click()` executed
7. New snapshot returned after each action
8. Results displayed in UI
9. `summarizationMiddleware` compresses context when threshold reached

### Communication Pattern

```
Background Service Worker          Content Script
        │                               │
        │  ──── { type: "snapshot" } ──▶ │
        │  ◀──── { yaml, refCount } ──── │  ◄── walks DOM + shadow roots
        │                               │
        │  ──── { type: "action",  ────▶ │
        │         action: "click",      │
        │         params: {ref} }       │
        │  ◀──── { success, snapshot }─ │  ◄── element.click()
```

Content script handles:
- DOM traversal including shadow DOM
- Accessible name extraction (aria-label, text content)
- Role detection (explicit + implicit)
- Click/type/hover via dispatchEvent
- Fresh snapshot after each action

---

## 2. Folder Structure

```
clients/chrome-extension/
├── manifest.json
├── package.json
├── tsconfig.json
├── vite.config.ts
├── .env.example
│
├── src/
│   ├── llm/                              # All LLM Logic
│   │   ├── index.ts
│   │   │
│   │   ├── agent/
│   │   │   ├── createSkillAgent.ts       # Uses createAgent from "langchain"
│   │   │   └── types.ts
│   │   │
│   │   ├── middleware/
│   │   │   ├── skillPromptMiddleware.ts  # dynamicSystemPromptMiddleware
│   │   │   └── index.ts
│   │   │
│   │   ├── tools/
│   │   │   ├── index.ts
│   │   │   ├── navigation.ts             # navigate, goBack, goForward, wait
│   │   │   ├── interaction.ts            # click, type, hover, selectOption (use ref)
│   │   │   ├── pageReading.ts            # snapshot, screenshot, getConsoleLogs
│   │   │   └── types.ts
│   │   │
│   │   └── skills/
│   │       ├── loader.ts
│   │       └── types.ts
│   │
│   ├── ui/                               # React UI (minimal)
│   │   ├── sidepanel/
│   │   │   ├── index.html
│   │   │   ├── main.tsx
│   │   │   └── App.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── SkillList.tsx
│   │   │   └── OutputDisplay.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useSkills.ts
│   │   │   └── useSkillExecution.ts
│   │   │
│   │   └── types.ts
│   │
│   ├── background/
│   │   └── index.ts                      # Service worker entry
│   │
│   ├── content/
│   │   ├── index.ts                      # Content script entry + message handler
│   │   ├── snapshot/
│   │   │   └── snapshotService.ts        # DOM walker + YAML serializer
│   │   └── actions/
│   │       └── executor.ts               # click, type, hover, scroll
│   │
│   └── shared/
│       ├── messaging.ts                  # Chrome message types
│       └── env.ts                        # Environment variable access
│
├── skills/                               # SKILL Prompt Files
│   ├── whatsapp-messages.prompt.md
│   └── README.md
│
├── evals/
│   └── run-eval.ts                       # Simple LangSmith evaluation script
│
└── scripts/
    └── build.ts                          # Build script
```

---

## 3. Environment Variables

All configuration via environment variables. No hardcoded strings.

### `.env.example`

```bash
# LLM Configuration
VITE_LLM_MODEL=gpt-4o
VITE_SUMMARIZATION_MODEL=gpt-4o-mini
VITE_TOKEN_THRESHOLD=4000
VITE_MESSAGES_TO_KEEP=20
VITE_MAX_TOOL_CALLS=50

# API Keys (VITE_ prefix for extension, plain for eval scripts)
VITE_OPENAI_API_KEY=
OPENAI_API_KEY=

# LangSmith (for evaluation)
LANGSMITH_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=chrome-extension-agent

# Extension
VITE_EXTENSION_NAME=Skill Runner
VITE_EXTENSION_VERSION=1.0.0
```

### Environment Access Pattern

```typescript
// src/shared/env.ts

import { z } from "zod";

const EnvSchema = z.object({
  LLM_MODEL: z.string().default("gpt-4o"),
  SUMMARIZATION_MODEL: z.string().default("gpt-4o-mini"),
  TOKEN_THRESHOLD: z.coerce.number().default(4000),
  MESSAGES_TO_KEEP: z.coerce.number().default(20),
  MAX_TOOL_CALLS: z.coerce.number().default(50),
  OPENAI_API_KEY: z.string(),
});

export type Env = z.infer<typeof EnvSchema>;

export function getEnv(): Env {
  return EnvSchema.parse({
    LLM_MODEL: import.meta.env.VITE_LLM_MODEL,
    SUMMARIZATION_MODEL: import.meta.env.VITE_SUMMARIZATION_MODEL,
    TOKEN_THRESHOLD: import.meta.env.VITE_TOKEN_THRESHOLD,
    MESSAGES_TO_KEEP: import.meta.env.VITE_MESSAGES_TO_KEEP,
    MAX_TOOL_CALLS: import.meta.env.VITE_MAX_TOOL_CALLS,
    OPENAI_API_KEY: import.meta.env.VITE_OPENAI_API_KEY,
  });
}
```

---

## 4. LangChain v1 Agent Pattern

### 4.1 Correct Imports

```typescript
import { createAgent, summarizationMiddleware, dynamicSystemPromptMiddleware } from "langchain";
import { tool } from "@langchain/core/tools";
import { HumanMessage, AIMessage, SystemMessage, ToolMessage } from "langchain";
import { z } from "zod";
```

### 4.2 Agent Creation

```typescript
// src/llm/agent/createSkillAgent.ts

import {
  createAgent,
  summarizationMiddleware,
  dynamicSystemPromptMiddleware,
} from "langchain";
import { MemorySaver } from "@langchain/langgraph";
import { z } from "zod";
import { browserTools } from "../tools";
import { getEnv } from "../../shared/env";

const SkillContextSchema = z.object({
  skillId: z.string(),
  skillPrompt: z.string(),
  tabId: z.number(),
});

type SkillContext = z.infer<typeof SkillContextSchema>;

export function createSkillAgent() {
  const env = getEnv();

  const skillPromptMiddleware = dynamicSystemPromptMiddleware<SkillContext>(
    (_state, runtime) => {
      const basePrompt = [
        "You are a browser automation assistant.",
        "You can interact with web pages using the provided tools.",
        "After each action, you will receive an ARIA accessibility snapshot of the page.",
        "Use natural language to describe elements (e.g., 'Send button', 'First chat in list').",
      ].join(" ");

      return `${basePrompt}\n\n## Current Skill Instructions\n\n${runtime.context.skillPrompt}`;
    }
  );

  return createAgent({
    model: env.LLM_MODEL,
    tools: browserTools,
    middleware: [
      skillPromptMiddleware,
      summarizationMiddleware({
        model: env.SUMMARIZATION_MODEL,
        trigger: { tokens: env.TOKEN_THRESHOLD },
        keep: { messages: env.MESSAGES_TO_KEEP },
      }),
    ],
    contextSchema: SkillContextSchema,
    checkpointer: new MemorySaver(),
  });
}

export async function executeSkill(
  agent: ReturnType<typeof createSkillAgent>,
  skillId: string,
  skillPrompt: string,
  tabId: number
) {
  const result = await agent.invoke(
    { messages: [{ role: "user", content: "Execute the skill instructions." }] },
    { context: { skillId, skillPrompt, tabId } }
  );
  return result;
}
```

---

## 5. Browser Tools (Adapted from MCP Patterns)

### 5.1 Tool Interface Pattern

```typescript
// src/llm/tools/types.ts

import { z } from "zod";

export interface ToolResult {
  content: string;
  snapshot?: string;
  isError?: boolean;
}

// Message types for content script communication
export const BrowserMessageTypes = {
  SNAPSHOT: "browser_snapshot",
  CLICK: "browser_click",
  TYPE: "browser_type",
  HOVER: "browser_hover",
  SELECT_OPTION: "browser_select_option",
  NAVIGATE: "browser_navigate",
  GO_BACK: "browser_go_back",
  GO_FORWARD: "browser_go_forward",
  PRESS_KEY: "browser_press_key",
  WAIT: "browser_wait",
  SCREENSHOT: "browser_screenshot",
  GET_CONSOLE_LOGS: "browser_get_console_logs",
  DRAG: "browser_drag",
  SCROLL: "browser_scroll",
} as const;

export type BrowserMessageType = typeof BrowserMessageTypes[keyof typeof BrowserMessageTypes];
```

### 5.2 Content Script Communication

```typescript
// src/llm/tools/messaging.ts

import type { BrowserMessageType } from "./types";

export async function sendToContentScript<T>(
  tabId: number,
  type: BrowserMessageType,
  payload: Record<string, unknown>
): Promise<T> {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, { type, payload }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (response?.error) {
        reject(new Error(response.error));
        return;
      }
      resolve(response?.data as T);
    });
  });
}

export async function captureSnapshot(tabId: number): Promise<string> {
  const url = await sendToContentScript<string>(tabId, "browser_snapshot", {});
  return url;
}
```

### 5.3 Navigation Tools

```typescript
// src/llm/tools/navigation.ts

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { sendToContentScript, captureSnapshot } from "./messaging";
import { BrowserMessageTypes } from "./types";

export const navigate = tool(
  async ({ url }, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.NAVIGATE, { url });
    const snapshot = await captureSnapshot(context.tabId);
    return `Navigated to ${url}\n\n${snapshot}`;
  },
  {
    name: "navigate",
    description: "Navigate to a URL. Returns page snapshot after loading.",
    schema: z.object({
      url: z.string().url().describe("URL to navigate to"),
    }),
  }
);

export const goBack = tool(
  async (_, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.GO_BACK, {});
    const snapshot = await captureSnapshot(context.tabId);
    return `Navigated back\n\n${snapshot}`;
  },
  {
    name: "go_back",
    description: "Go back in browser history. Returns page snapshot.",
    schema: z.object({}),
  }
);

export const goForward = tool(
  async (_, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.GO_FORWARD, {});
    const snapshot = await captureSnapshot(context.tabId);
    return `Navigated forward\n\n${snapshot}`;
  },
  {
    name: "go_forward",
    description: "Go forward in browser history. Returns page snapshot.",
    schema: z.object({}),
  }
);

export const wait = tool(
  async ({ seconds }) => {
    await new Promise((resolve) => setTimeout(resolve, seconds * 1000));
    return `Waited ${seconds} seconds`;
  },
  {
    name: "wait",
    description: "Wait for a specified number of seconds.",
    schema: z.object({
      seconds: z.number().min(0.1).max(30).describe("Seconds to wait (max 30)"),
    }),
  }
);
```

### 5.4 Interaction Tools

```typescript
// src/llm/tools/interaction.ts

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { sendToContentScript, captureSnapshot } from "./messaging";
import { BrowserMessageTypes } from "./types";

export const click = tool(
  async ({ element }, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.CLICK, { element });
    const snapshot = await captureSnapshot(context.tabId);
    return `Clicked "${element}"\n\n${snapshot}`;
  },
  {
    name: "click",
    description: "Click an element using natural language description (e.g., 'Send button', 'First chat in list'). Returns page snapshot.",
    schema: z.object({
      element: z.string().describe("Natural language description of element to click"),
    }),
  }
);

export const type = tool(
  async ({ element, text, clearFirst }, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.TYPE, { element, text, clearFirst });
    const snapshot = await captureSnapshot(context.tabId);
    return `Typed "${text}" into "${element}"\n\n${snapshot}`;
  },
  {
    name: "type",
    description: "Type text into an input element using natural language description. Returns page snapshot.",
    schema: z.object({
      element: z.string().describe("Natural language description of input element"),
      text: z.string().describe("Text to type"),
      clearFirst: z.boolean().optional().default(false).describe("Clear existing text first"),
    }),
  }
);

export const hover = tool(
  async ({ element }, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.HOVER, { element });
    const snapshot = await captureSnapshot(context.tabId);
    return `Hovered over "${element}"\n\n${snapshot}`;
  },
  {
    name: "hover",
    description: "Hover over an element to reveal dropdowns or tooltips. Returns page snapshot.",
    schema: z.object({
      element: z.string().describe("Natural language description of element to hover"),
    }),
  }
);

export const selectOption = tool(
  async ({ element, option }, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.SELECT_OPTION, { element, option });
    const snapshot = await captureSnapshot(context.tabId);
    return `Selected "${option}" from "${element}"\n\n${snapshot}`;
  },
  {
    name: "select_option",
    description: "Select an option from a dropdown element. Returns page snapshot.",
    schema: z.object({
      element: z.string().describe("Natural language description of dropdown element"),
      option: z.string().describe("Option text or value to select"),
    }),
  }
);

export const pressKey = tool(
  async ({ key }, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.PRESS_KEY, { key });
    const snapshot = await captureSnapshot(context.tabId);
    return `Pressed key "${key}"\n\n${snapshot}`;
  },
  {
    name: "press_key",
    description: "Press a keyboard key or combination (e.g., 'Enter', 'Tab', 'Ctrl+C'). Returns page snapshot.",
    schema: z.object({
      key: z.string().describe("Key name or combination"),
    }),
  }
);

export const drag = tool(
  async ({ startElement, endElement }, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.DRAG, { startElement, endElement });
    const snapshot = await captureSnapshot(context.tabId);
    return `Dragged from "${startElement}" to "${endElement}"\n\n${snapshot}`;
  },
  {
    name: "drag",
    description: "Drag an element to another location. Returns page snapshot.",
    schema: z.object({
      startElement: z.string().describe("Element to drag from"),
      endElement: z.string().describe("Element to drag to"),
    }),
  }
);

export const scroll = tool(
  async ({ direction, amount }, { context }) => {
    await sendToContentScript(context.tabId, BrowserMessageTypes.SCROLL, { direction, amount });
    const snapshot = await captureSnapshot(context.tabId);
    return `Scrolled ${direction} ${amount}px\n\n${snapshot}`;
  },
  {
    name: "scroll",
    description: "Scroll the page in a direction. Returns page snapshot.",
    schema: z.object({
      direction: z.enum(["up", "down"]).describe("Scroll direction"),
      amount: z.number().optional().default(500).describe("Pixels to scroll"),
    }),
  }
);
```

### 5.5 Page Reading Tools

```typescript
// src/llm/tools/pageReading.ts

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { sendToContentScript, captureSnapshot } from "./messaging";
import { BrowserMessageTypes } from "./types";

export const snapshot = tool(
  async (_, { context }) => {
    const result = await captureSnapshot(context.tabId);
    return result;
  },
  {
    name: "snapshot",
    description: "Capture current page structure as ARIA accessibility tree. Shows all interactive elements and text content.",
    schema: z.object({}),
  }
);

export const screenshot = tool(
  async (_, { context }) => {
    const base64 = await sendToContentScript<string>(
      context.tabId,
      BrowserMessageTypes.SCREENSHOT,
      {}
    );
    return { type: "image", data: base64, mimeType: "image/png" };
  },
  {
    name: "screenshot",
    description: "Capture a visual screenshot of the current page.",
    schema: z.object({}),
  }
);

export const getConsoleLogs = tool(
  async ({ filter }, { context }) => {
    const logs = await sendToContentScript<string>(
      context.tabId,
      BrowserMessageTypes.GET_CONSOLE_LOGS,
      { filter }
    );
    return logs;
  },
  {
    name: "get_console_logs",
    description: "Get JavaScript console messages. Useful for debugging.",
    schema: z.object({
      filter: z.enum(["all", "errors", "warnings"]).optional().default("all"),
    }),
  }
);
```

### 5.6 Tool Index

```typescript
// src/llm/tools/index.ts

import { navigate, goBack, goForward, wait } from "./navigation";
import { click, type, hover, selectOption, pressKey, drag, scroll } from "./interaction";
import { snapshot, screenshot, getConsoleLogs } from "./pageReading";

export const browserTools = [
  // Navigation
  navigate,
  goBack,
  goForward,
  wait,
  // Interaction
  click,
  type,
  hover,
  selectOption,
  pressKey,
  drag,
  scroll,
  // Page reading
  snapshot,
  screenshot,
  getConsoleLogs,
];
```

---

## 6. Browser Control (Content Script)

Content script approach for Chrome Web Store compatibility. No `debugger` permission needed.

### 6.1 Approach Comparison

| Approach | Pros | Cons |
|----------|------|------|
| CDP (debugger) | Native accessibility tree | Scary permission, store risk |
| **Content Script** | Easy approval, no warnings | Must handle shadow DOM manually |

### 6.2 Architecture

```
Background Script                    Content Script (injected)
      │                                     │
      │  ──── getSnapshot ────────────────▶ │
      │  ◀──── YAML + refMap ────────────── │ ◄── walks DOM + shadowRoots
      │                                     │
      │  ──── click ref_3 ────────────────▶ │
      │  ◀──── success + new snapshot ───── │ ◄── element.click()
```

### 6.3 Snapshot Service (Content Script)

Walks DOM including shadow roots, builds accessibility-like tree with refs.

```typescript
// src/content/snapshot/snapshotService.ts

interface SnapshotNode {
  role: string;
  name: string;
  ref?: string;
  properties: Record<string, boolean>;
  children: SnapshotNode[];
}

// Store ref -> element mapping for actions
const refMap = new Map<string, Element>();
let refCounter = 0;

export function captureSnapshot(): { yaml: string; refCount: number } {
  refMap.clear();
  refCounter = 0;

  const tree = walkNode(document.body);
  const yaml = serializeToYaml(tree, 0);

  return {
    yaml: `- Page URL: ${location.href}\n- Page Title: ${document.title}\n\n${yaml}`,
    refCount: refCounter,
  };
}

function walkNode(node: Node): SnapshotNode | null {
  if (node.nodeType === Node.TEXT_NODE) {
    const text = node.textContent?.trim();
    if (text) return { role: "text", name: text, properties: {}, children: [] };
    return null;
  }

  if (!(node instanceof Element)) return null;

  const role = getRole(node);
  const name = getAccessibleName(node);

  // Skip non-semantic containers
  if (role === "generic" && !name) {
    const children = getChildren(node).map(walkNode).filter(Boolean) as SnapshotNode[];
    if (children.length === 1) return children[0];
    if (children.length === 0) return null;
    return { role: "group", name: "", properties: {}, children };
  }

  const result: SnapshotNode = {
    role,
    name,
    properties: getProperties(node),
    children: getChildren(node).map(walkNode).filter(Boolean) as SnapshotNode[],
  };

  // Assign ref to interactive elements
  if (isInteractive(node, role)) {
    const ref = `ref_${refCounter++}`;
    result.ref = ref;
    refMap.set(ref, node);
  }

  return result;
}

function getChildren(element: Element): Node[] {
  const children: Node[] = [];

  // Regular children
  children.push(...Array.from(element.childNodes));

  // Pierce shadow DOM
  if (element.shadowRoot) {
    children.push(...Array.from(element.shadowRoot.childNodes));
  }

  // Handle slots (for shadow DOM)
  if (element instanceof HTMLSlotElement) {
    children.push(...element.assignedNodes());
  }

  return children;
}

function getRole(element: Element): string {
  // Explicit ARIA role
  const ariaRole = element.getAttribute("role");
  if (ariaRole) return ariaRole;

  // Implicit roles from tag
  const tagRoles: Record<string, string> = {
    button: "button",
    a: "link",
    input: getInputRole(element as HTMLInputElement),
    textarea: "textbox",
    select: "combobox",
    img: "image",
    h1: "heading",
    h2: "heading",
    h3: "heading",
    nav: "navigation",
    main: "main",
    header: "banner",
    footer: "contentinfo",
    ul: "list",
    ol: "list",
    li: "listitem",
  };

  return tagRoles[element.tagName.toLowerCase()] ?? "generic";
}

function getInputRole(input: HTMLInputElement): string {
  const typeRoles: Record<string, string> = {
    text: "textbox",
    search: "searchbox",
    email: "textbox",
    password: "textbox",
    checkbox: "checkbox",
    radio: "radio",
    button: "button",
    submit: "button",
  };
  return typeRoles[input.type] ?? "textbox";
}

function getAccessibleName(element: Element): string {
  // aria-label takes precedence
  const ariaLabel = element.getAttribute("aria-label");
  if (ariaLabel) return ariaLabel;

  // aria-labelledby
  const labelledBy = element.getAttribute("aria-labelledby");
  if (labelledBy) {
    const labelEl = document.getElementById(labelledBy);
    if (labelEl) return labelEl.textContent?.trim() ?? "";
  }

  // For inputs, check associated label
  if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
    const label = document.querySelector(`label[for="${element.id}"]`);
    if (label) return label.textContent?.trim() ?? "";
  }

  // Placeholder for inputs
  if (element instanceof HTMLInputElement) {
    if (element.placeholder) return element.placeholder;
  }

  // Button/link text content
  if (["button", "a"].includes(element.tagName.toLowerCase())) {
    return element.textContent?.trim() ?? "";
  }

  // Alt text for images
  if (element instanceof HTMLImageElement) {
    return element.alt ?? "";
  }

  // Title attribute
  const title = element.getAttribute("title");
  if (title) return title;

  return "";
}

function getProperties(element: Element): Record<string, boolean> {
  const props: Record<string, boolean> = {};

  if (element.hasAttribute("disabled")) props.disabled = true;
  if (element.getAttribute("aria-disabled") === "true") props.disabled = true;
  if (element.getAttribute("aria-expanded") === "true") props.expanded = true;
  if (element.getAttribute("aria-selected") === "true") props.selected = true;
  if (element.getAttribute("aria-checked") === "true") props.checked = true;
  if (document.activeElement === element) props.focused = true;

  if (element instanceof HTMLInputElement) {
    if (element.type === "checkbox" && element.checked) props.checked = true;
  }

  return props;
}

function isInteractive(element: Element, role: string): boolean {
  const interactiveRoles = [
    "button", "link", "textbox", "searchbox", "checkbox", "radio",
    "combobox", "listbox", "option", "menuitem", "tab", "switch",
  ];

  if (interactiveRoles.includes(role)) return true;

  // Elements with click handlers or tabindex
  if (element.hasAttribute("onclick")) return true;
  if (element.getAttribute("tabindex") === "0") return true;

  return false;
}

function serializeToYaml(node: SnapshotNode | null, depth: number): string {
  if (!node) return "";

  const indent = "  ".repeat(depth);
  let line = `${indent}- ${node.role}`;

  if (node.name) line += ` "${node.name}"`;
  if (node.ref) line += ` [${node.ref}]`;

  const propStr = Object.entries(node.properties)
    .filter(([, v]) => v)
    .map(([k]) => k)
    .join(", ");
  if (propStr) line += ` [${propStr}]`;

  const childYaml = node.children
    .map(c => serializeToYaml(c, depth + 1))
    .filter(Boolean)
    .join("\n");

  return childYaml ? `${line}\n${childYaml}` : line;
}

// Export for action execution
export function getElementByRef(ref: string): Element | null {
  return refMap.get(ref) ?? null;
}
```

### 6.4 Action Executor (Content Script)

```typescript
// src/content/actions/executor.ts

import { getElementByRef, captureSnapshot } from "../snapshot/snapshotService";

export async function executeAction(
  action: string,
  params: Record<string, unknown>
): Promise<{ success: boolean; snapshot: string; error?: string }> {
  try {
    switch (action) {
      case "click":
        await clickElement(params.ref as string);
        break;
      case "type":
        await typeInElement(params.ref as string, params.text as string);
        break;
      case "hover":
        await hoverElement(params.ref as string);
        break;
      case "scroll":
        await scrollPage(params.direction as "up" | "down");
        break;
      default:
        throw new Error(`Unknown action: ${action}`);
    }

    // Return fresh snapshot after action
    const { yaml } = captureSnapshot();
    return { success: true, snapshot: yaml };
  } catch (error) {
    const { yaml } = captureSnapshot();
    return { success: false, snapshot: yaml, error: String(error) };
  }
}

async function clickElement(ref: string): Promise<void> {
  const element = getElementByRef(ref);
  if (!element) throw new Error(`Element not found: ${ref}`);

  // Scroll into view
  element.scrollIntoView({ behavior: "smooth", block: "center" });
  await sleep(100);

  // Dispatch click events (more reliable than .click())
  const rect = element.getBoundingClientRect();
  const x = rect.left + rect.width / 2;
  const y = rect.top + rect.height / 2;

  element.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, clientX: x, clientY: y }));
  element.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: x, clientY: y }));
  element.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: x, clientY: y }));

  await sleep(100);
}

async function typeInElement(ref: string, text: string): Promise<void> {
  const element = getElementByRef(ref);
  if (!element) throw new Error(`Element not found: ${ref}`);

  if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement)) {
    // For contenteditable elements
    if (element.getAttribute("contenteditable") === "true") {
      element.focus();
      document.execCommand("insertText", false, text);
      return;
    }
    throw new Error(`Element is not typeable: ${ref}`);
  }

  element.focus();
  element.value = text;

  // Dispatch input events for frameworks (React, Vue, etc.)
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

async function hoverElement(ref: string): Promise<void> {
  const element = getElementByRef(ref);
  if (!element) throw new Error(`Element not found: ${ref}`);

  element.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
  element.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
}

async function scrollPage(direction: "up" | "down"): Promise<void> {
  const amount = direction === "up" ? -500 : 500;
  window.scrollBy({ top: amount, behavior: "smooth" });
  await sleep(300);
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

### 6.5 Message Handler (Content Script)

```typescript
// src/content/index.ts

import { captureSnapshot } from "./snapshot/snapshotService";
import { executeAction } from "./actions/executor";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handleMessage(message).then(sendResponse);
  return true; // async response
});

async function handleMessage(message: { type: string; payload?: Record<string, unknown> }) {
  switch (message.type) {
    case "snapshot":
      return captureSnapshot();

    case "action":
      return executeAction(
        message.payload?.action as string,
        message.payload?.params as Record<string, unknown>
      );

    default:
      return { error: `Unknown message type: ${message.type}` };
  }
}
```

### 6.6 Snapshot Output Example

```yaml
- Page URL: https://web.whatsapp.com
- Page Title: WhatsApp

- main
  - navigation "Chat list"
    - list "Chats"
      - listitem "John Doe" [ref_0]
        - text "Hey, how are you?"
      - listitem "Jane Smith" [ref_1]
        - text "See you tomorrow"
  - region "Chat"
    - heading "John Doe"
    - list "Messages"
      - listitem
        - text "Hey!"
      - listitem
        - text "What's up?"
    - textbox "Type a message" [ref_5] [focused]
    - button "Send" [ref_6]
```

Agent sees refs, returns: `click ref="ref_6"` → Content script executes.

### 6.7 Shadow DOM Handling

The `getChildren()` function automatically pierces shadow DOM:

```typescript
// Handles:
// 1. Regular children
// 2. Shadow root children (element.shadowRoot)
// 3. Slotted content (for web components)

function getChildren(element: Element): Node[] {
  const children: Node[] = [];
  children.push(...Array.from(element.childNodes));

  if (element.shadowRoot) {
    children.push(...Array.from(element.shadowRoot.childNodes));
  }

  if (element instanceof HTMLSlotElement) {
    children.push(...element.assignedNodes());
  }

  return children;
}
```

### 6.8 Limitations vs CDP

| Feature | Content Script | CDP |
|---------|---------------|-----|
| Shadow DOM | ✅ Manual traversal | ✅ Native |
| IFrames (same origin) | ✅ Via all_frames | ✅ |
| IFrames (cross origin) | ❌ Blocked | ✅ |
| Closed shadow roots | ❌ Cannot access | ✅ |
| Keyboard events | ⚠️ Limited | ✅ Full |

For WhatsApp Web: Works for most interactions. WhatsApp uses open shadow DOM which we can traverse.

---

## 7. Evaluations (LangSmith SDK)

LLM-as-judge evaluation using `evaluate()` from LangSmith SDK with `CORRECTNESS_PROMPT` from openevals.

### 7.1 Evaluation Script

```typescript
// evals/run-eval.ts

import "dotenv/config";
import { Client } from "langsmith";
import { evaluate } from "langsmith/evaluation";
import { traceable } from "langsmith/traceable";
import { createLLMAsJudge, CORRECTNESS_PROMPT } from "openevals";
import { executeSkill, createSkillAgent } from "../src/llm/agent/createSkillAgent";

const langsmith = new Client();

// 1. LLM-as-judge evaluator (uses OPENAI_API_KEY from .env)
const correctnessEvaluator = createLLMAsJudge({
  prompt: CORRECTNESS_PROMPT,
  model: "openai:gpt-4o-mini",  // Uses OPENAI_API_KEY env var automatically
});

// 2. Target function - the thing we're evaluating
const runSkill = traceable(
  async (inputs: { skillPrompt: string; tabId: number }) => {
    const agent = createSkillAgent();
    const result = await executeSkill(agent, "eval", inputs.skillPrompt, inputs.tabId);
    return { output: result.messages.at(-1)?.content ?? "" };
  },
  { name: "runSkill" }
);

// 3. Dataset - inputs + reference outputs
const examples = [
  {
    inputs: { skillPrompt: "Navigate to https://example.com", tabId: 1 },
    outputs: { expected: "Successfully navigated to the URL" },
  },
  {
    inputs: { skillPrompt: "Click the Submit button", tabId: 1 },
    outputs: { expected: "Clicked on the submit button element" },
  },
  {
    inputs: { skillPrompt: "Type hello into the search box", tabId: 1 },
    outputs: { expected: "Typed the text into the search input field" },
  },
];

// 4. Run evaluation
async function main() {
  const datasetName = "Browser Agent Skills";
  let dataset;
  try {
    dataset = await langsmith.readDataset({ datasetName });
  } catch {
    dataset = await langsmith.createDataset(datasetName);
    await langsmith.createExamples({
      datasetId: dataset.id,
      inputs: examples.map((e) => e.inputs),
      outputs: examples.map((e) => e.outputs),
    });
  }

  // Run eval with LLM-as-judge
  await evaluate((inputs) => runSkill(inputs), {
    data: datasetName,
    evaluators: [correctnessEvaluator],
    experimentPrefix: "browser-agent-eval",
    maxConcurrency: 2,
  });
}

main();
```

### 7.2 Package Script

```json
{
  "scripts": {
    "eval": "npx tsx evals/run-eval.ts"
  }
}
```

### 7.3 Run Evaluation

```bash
# Required env vars in .env:
# OPENAI_API_KEY=sk-...      (for LLM-as-judge)
# LANGSMITH_API_KEY=ls-...   (for LangSmith)
# LANGSMITH_TRACING=true

# Run
pnpm eval
```

Results appear in LangSmith UI under Experiments.

---

## 8. Chrome Extension Setup (Manual, No Boilerplate)

### 8.1 Manifest V3

```json
// manifest.json

{
  "manifest_version": 3,
  "name": "Skill Runner",
  "version": "1.0.0",
  "description": "Browser automation with LangChain agents",

  "permissions": [
    "sidePanel",
    "activeTab",
    "scripting",
    "storage"
  ],

  "host_permissions": [
    "<all_urls>"
  ],

  "side_panel": {
    "default_path": "sidepanel.html"
  },

  "background": {
    "service_worker": "dist/background/index.js",
    "type": "module"
  },

  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["dist/content/index.js"],
      "run_at": "document_idle"
    }
  ],

  "action": {
    "default_title": "Open Skill Runner"
  }
}
```

### 8.2 Vite Configuration

```typescript
// vite.config.ts

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        sidepanel: resolve(__dirname, "src/ui/sidepanel/index.html"),
        background: resolve(__dirname, "src/background/index.ts"),
        content: resolve(__dirname, "src/content/index.ts"),
      },
      output: {
        entryFileNames: "[name]/index.js",
        chunkFileNames: "chunks/[name]-[hash].js",
      },
    },
    outDir: "dist",
    emptyDirBeforeWrite: true,
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
});
```

### 8.3 Package Configuration

```json
// package.json

{
  "name": "skill-runner-extension",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite build --watch",
    "build": "vite build",
    "eval": "vitest run --config ls.vitest.config.ts",
    "eval:watch": "vitest --config ls.vitest.config.ts",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "langchain": "^1.0.0",
    "@langchain/core": "^1.0.0",
    "@langchain/langgraph": "^1.0.0",
    "@langchain/openai": "^1.0.0",
    "langsmith": "^0.3.13",
    "openevals": "^0.1.0",
    "openai": "^4.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zod": "^3.22.0",
    "gray-matter": "^4.0.3"
  },
  "devDependencies": {
    "@types/chrome": "^0.0.260",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "dotenv": "^16.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vitest": "^1.2.0"
  }
}
```

### 8.4 TypeScript Configuration

```json
// tsconfig.json

{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    },
    "types": ["chrome", "vite/client"]
  },
  "include": ["src/**/*", "evals/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

---

## 9. Development Phases

### Phase 1: Chrome Extension Foundation (Manual Setup)

- Create `manifest.json` following Manifest V3 spec
- Set up Vite build configuration for multi-entry (sidepanel, background, content)
- Create folder structure as specified
- Set up environment variables with Zod validation
- Configure TypeScript with Chrome types
- Test extension loads in Chrome

### Phase 2: Message Passing Infrastructure

- Define message types in `src/shared/messaging.ts`
- Implement background script message handler
- Implement content script message listener
- Test bi-directional communication between background and content scripts

### Phase 3: Content Script Browser Control

- Implement `snapshotService.ts` - DOM walker with shadow DOM support
- Implement role detection (explicit ARIA + implicit from tags)
- Implement accessible name extraction (aria-label, text, placeholder)
- Serialize to YAML with ref IDs
- Implement `executor.ts` for click/type/hover via dispatchEvent

### Phase 4: Browser Tools

- Implement all navigation tools (navigate, goBack, goForward, wait)
- Implement all interaction tools (click, type, hover, selectOption, pressKey, drag, scroll)
- Implement page reading tools (snapshot, screenshot, getConsoleLogs)
- Wire tools to content script communication

### Phase 5: Agent Core

- Implement `createSkillAgent.ts` with `createAgent` from langchain
- Implement `skillPromptMiddleware` with `dynamicSystemPromptMiddleware`
- Configure `summarizationMiddleware`
- Implement skill loader for `.prompt.md` files

### Phase 6: UI

- Create side panel HTML entry point
- Implement SkillList component
- Implement OutputDisplay component
- Implement useSkills and useSkillExecution hooks
- Wire click-to-execute flow

### Phase 7: Integration & Evaluation

- Create `evals/run-eval.ts` using LangSmith SDK
- Run `pnpm eval` to verify agent correctness
- End-to-end test with WhatsApp skill
- Fix any failures

---

## 10. Tool Summary

| Tool | Purpose | Returns |
|------|---------|---------|
| `navigate` | Go to URL | snapshot |
| `go_back` | Browser back | snapshot |
| `go_forward` | Browser forward | snapshot |
| `wait` | Delay | confirmation |
| `click` | Click element (natural language) | snapshot |
| `type` | Type text (natural language) | snapshot |
| `hover` | Hover element | snapshot |
| `select_option` | Select dropdown | snapshot |
| `press_key` | Keyboard input | snapshot |
| `drag` | Drag and drop | snapshot |
| `scroll` | Scroll page | snapshot |
| `snapshot` | Get ARIA tree | ARIA snapshot |
| `screenshot` | Visual capture | image |
| `get_console_logs` | JS console | logs |

---

## 11. Evaluation

Single evaluation script (`evals/run-eval.ts`) that:
1. Defines target function (agent skill execution)
2. Creates dataset with inputs + expected outputs
3. Runs simple correctness evaluator
4. Calls `evaluate()` from `langsmith/evaluation`

Run with `pnpm eval`. Results in LangSmith UI.

---

## 12. Code Quality Rules

### Mandatory

- No `any` type (use `unknown` or proper types)
- No hardcoded strings (use environment variables)
- Use LangChain v1 built-ins (`createAgent`, `summarizationMiddleware`)
- All tools use Zod schema validation

### Anti-Over-Engineering

- NO features beyond this plan
- NO complex state management
- NO UI libraries beyond React
- Simple > clever

---

## 13. Verified Patterns

| Aspect | Pattern | Source |
|--------|---------|--------|
| Agent creation | `createAgent` from `"langchain"` | context-engineering.mdx |
| System prompt | `dynamicSystemPromptMiddleware` | context-engineering.mdx |
| Summarization | `summarizationMiddleware` | context-engineering.mdx |
| Tool definition | `tool()` from `@langchain/core/tools` with Zod schema | context-engineering.mdx |
| Messages | `HumanMessage`, `AIMessage`, etc from `"langchain"` | messages.mdx |
| Evaluation | `evaluate()` from `langsmith/evaluation` | evaluate-llm-application.mdx |
| Evaluator | `createLLMAsJudge` + `CORRECTNESS_PROMPT` from `openevals` | openevals package |
| Browser control | Content script DOM traversal + shadow DOM | Chrome extension pattern |
| Element selection | ref IDs assigned during DOM walk | Similar to Playwright MCP |

---

*Plan verified against LangChain v1 documentation, LangSmith evaluation docs, and Browser MCP patterns*
*Status: Ready for Implementation*
