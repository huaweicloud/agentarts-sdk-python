// Thin REST client for the AgentArts Memory data plane.
//
// Endpoints mirror the data-plane branch of
// src/agentarts/sdk/service/memory_service.py (Bearer auth — no request
// signing).

import { DEFAULT_TIMEOUT_MS } from "./config.js";

/** Error raised for non-2xx API responses or network failures. */
export class MemoryApiError extends Error {
  constructor(
    /** HTTP status code; 0 = no HTTP response. */
    readonly status: number,
    readonly errorCode: string,
    readonly errorMsg: string,
  ) {
    super(`[${errorCode}] ${errorMsg}`);
    this.name = "MemoryApiError";
  }
}

export interface SearchRequestBody {
  query: string;
  strategy_type?: string;
  top_k?: number;
  min_score?: number;
  actor_id?: string;
  start_time?: number;
  end_time?: number;
  rerank?: boolean;
}

/** Search hit as returned by the backend: the memory record plus its score. */
export interface SearchRecord {
  record?: unknown;
  score?: number;
}

export interface SearchResponse {
  records?: SearchRecord[];
  results?: SearchRecord[];
  total?: number;
  query?: string;
}

export class MemoryDataPlane {
  constructor(
    private readonly baseUrl: string,
    private readonly apiKey: string,
    private readonly spaceId: string,
    private readonly timeoutMs: number = DEFAULT_TIMEOUT_MS,
  ) {}

  /** POST /v1/core/spaces/{space_id}/memories/search */
  async searchMemories(body: SearchRequestBody): Promise<SearchResponse> {
    return this.request<SearchResponse>(
      "POST",
      `/v1/core/spaces/${this.spaceId}/memories/search`,
      body,
    );
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    if (!this.apiKey) {
      throw new MemoryApiError(
        0,
        "AUTH_ERROR",
        "API Key is required for data plane operations. " +
          "Set the HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable.",
      );
    }
    if (!this.spaceId) {
      throw new MemoryApiError(
        0,
        "AUTH_ERROR",
        "Space ID is required. Set the AGENTARTS_MEMORY_SPACE_ID environment variable.",
      );
    }

    let res: Response;
    try {
      res = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(this.timeoutMs),
      });
    } catch (e) {
      throw new MemoryApiError(
        0,
        "NETWORK_ERROR",
        e instanceof Error ? e.message : String(e),
      );
    }

    if (res.status === 204) return {} as T;

    if (res.ok) {
      const contentType = res.headers.get("content-type") ?? "";
      if (contentType.startsWith("application/json")) {
        try {
          return (await res.json()) as T;
        } catch (e) {
          throw new MemoryApiError(
            res.status,
            "PARSE_ERROR",
            `Failed to parse JSON response: ${e instanceof Error ? e.message : String(e)}`,
          );
        }
      }
      return { response: await res.text() } as T;
    }

    // Non-2xx: surface the backend error_code / error_msg when available.
    let errorCode = "UNKNOWN_ERROR";
    let errorMsg = `HTTP ${res.status}`;
    try {
      const err = (await res.json()) as { error_code?: string; error_msg?: string };
      if (err.error_code) errorCode = err.error_code;
      if (err.error_msg) errorMsg = err.error_msg;
    } catch {
      // keep defaults
    }
    throw new MemoryApiError(res.status, errorCode, errorMsg);
  }
}
