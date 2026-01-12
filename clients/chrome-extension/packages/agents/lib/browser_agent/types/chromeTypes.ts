export interface ScreenshotResponse {
  success: boolean;
  screenshot?: string;
  viewport?: { width: number; height: number };
  error?: string;
}

export interface BrowserActionResponse {
  success: boolean;
  error?: string;
  details?: {
    action: string;
    details: string;
  };
}

export interface ToggleGridResponse {
  success: boolean;
  error?: string;
}
