import type { ProblemDetails } from '../types/problemDetails';

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  constructor(public readonly status: number, message: string, public readonly problem?: ProblemDetails) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<{ data: T; etag?: string }> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
    });
  } catch (error) {
    if (init.signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw error;
    throw new ApiError(0, 'The API is unavailable. Check the connection and try again.');
  }
  if (!response.ok) {
    let problem: ProblemDetails | undefined;
    try { problem = await response.json() as ProblemDetails; } catch { /* non-JSON responses are kept generic */ }
    throw new ApiError(response.status, problem?.detail ?? 'The request could not be completed.', problem);
  }
  if (response.status === 204) return { data: undefined as T, etag: response.headers.get('ETag') ?? undefined };
  return { data: await response.json() as T, etag: response.headers.get('ETag') ?? undefined };
}
