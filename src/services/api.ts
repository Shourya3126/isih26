/**
 * API client for SocialScope backend.
 *
 * All /api/* requests are proxied by Vite to the FastAPI backend
 * at http://127.0.0.1:8000 during development.
 */

const API_BASE = '/api';

// ── Types ────────────────────────────────────────────────────────────

export interface CollectionStartRequest {
  topic: string;
  keywords: string[];
  hashtags: string[];
  handles: string[];
  lookback_hours: number;
  target_items: number;
}

export interface CollectionStartResponse {
  job_id: string;
  platform: string;
  status: string;
  message: string;
}

export interface ChannelError {
  channel: string;
  error: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'partial';
  platform: string;
  progress: number;
  channels_checked: number;
  channels_total: number;
  messages_scanned: number;
  relevant_items: number;
  duplicates_removed: number;
  final_items: number;
  target_items: number;
  current_channel: string;
  topic: string;
  lookback_hours: number;
  error_message: string;
  channel_errors: ChannelError[];
  created_at: string;
  updated_at: string;
}

export interface SocialEventItem {
  event_id: string;
  platform: string;
  event_type: string;
  channel_id: string | null;
  channel_username: string | null;
  channel_title: string | null;
  message_id: number | null;
  author_id: string | null;
  author_username: string | null;
  author_display_name: string | null;
  content_text: string | null;
  timestamp: string | null;
  views: number;
  replies: number;
  forwards: number;
  relevance_score: number;
  matched_keywords: string[];
  matched_hashtags: string[];
}

export interface JobResultsResponse {
  job_id: string;
  platform: string;
  status: string;
  query: { topic: string; lookback_hours: number };
  statistics: {
    channels_checked: number;
    messages_scanned: number;
    relevant_messages: number;
    duplicates_removed: number;
    final_items: number;
  };
  items: SocialEventItem[];
}

export interface TelegramStatusResponse {
  connected: boolean;
  status: 'connected' | 'disconnected' | 'invalid_credentials';
  message: string;
}

// ── API Functions ────────────────────────────────────────────────────

/**
 * Start a Telegram collection pipeline.
 * Returns immediately with a job_id; collection runs in the background.
 */
export async function startTelegramCollection(
  params: CollectionStartRequest
): Promise<CollectionStartResponse> {
  const res = await fetch(`${API_BASE}/collection/telegram/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Get the current status and progress of a collection job.
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/collection/${encodeURIComponent(jobId)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Get the collected items for a completed (or partial) job.
 */
export async function getJobResults(jobId: string): Promise<JobResultsResponse> {
  const res = await fetch(`${API_BASE}/collection/${encodeURIComponent(jobId)}/results`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Check whether the Telegram session is authenticated.
 */
export async function getTelegramConnectionStatus(): Promise<TelegramStatusResponse> {
  const res = await fetch(`${API_BASE}/collection/telegram/status`);
  if (!res.ok) {
    // If backend is not running, return disconnected
    return {
      connected: false,
      status: 'disconnected',
      message: 'Backend not reachable',
    };
  }
  return res.json();
}

/**
 * Get all collected events across all jobs (for Evidence Vault).
 */
export async function getAllEvents(limit: number = 200): Promise<{ total: number; items: SocialEventItem[] }> {
  const res = await fetch(`${API_BASE}/collection/events/all?limit=${limit}`);
  if (!res.ok) {
    return { total: 0, items: [] };
  }
  return res.json();
}
