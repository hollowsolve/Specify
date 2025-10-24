import {
  AnalysisRequest,
  AnalysisResult,
  SpecificationRequest,
  SpecificationResult,
  RefinementRequest,
  RefinementResult,
  ExecutionRequest,
  ExecutionResult,
  Session,
} from '@/types'

class APIClient {
  private baseURL: string
  private defaultHeaders: HeadersInit

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const config: RequestInit = {
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new APIError(
          response.status,
          errorData.message || response.statusText,
          errorData
        )
      }

      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      }

      return response.text() as unknown as T
    } catch (error) {
      if (error instanceof APIError) {
        throw error
      }
      throw new APIError(0, 'Network error occurred', { originalError: error })
    }
  }

  // Analysis endpoints
  async analyzePrompt(request: AnalysisRequest): Promise<AnalysisResult> {
    return this.request<AnalysisResult>('/api/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getAnalysis(id: string): Promise<AnalysisResult> {
    return this.request<AnalysisResult>(`/api/analyze/${id}`)
  }

  // Specification endpoints
  async generateSpecification(request: SpecificationRequest): Promise<SpecificationResult> {
    return this.request<SpecificationResult>('/api/specify', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getSpecification(id: string): Promise<SpecificationResult> {
    return this.request<SpecificationResult>(`/api/specify/${id}`)
  }

  // Refinement endpoints
  async refineSpecification(request: RefinementRequest): Promise<RefinementResult> {
    return this.request<RefinementResult>('/api/refine', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getRefinement(id: string): Promise<RefinementResult> {
    return this.request<RefinementResult>(`/api/refine/${id}`)
  }

  // Execution endpoints
  async executeSpecification(request: ExecutionRequest): Promise<ExecutionResult> {
    return this.request<ExecutionResult>('/api/execute', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getExecution(id: string): Promise<ExecutionResult> {
    return this.request<ExecutionResult>(`/api/execute/${id}`)
  }

  async stopExecution(id: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/api/execute/${id}/stop`, {
      method: 'POST',
    })
  }

  // Session management
  async getSessions(): Promise<Session[]> {
    return this.request<Session[]>('/api/sessions')
  }

  async getSession(id: string): Promise<Session> {
    return this.request<Session>(`/api/sessions/${id}`)
  }

  async createSession(name: string): Promise<Session> {
    return this.request<Session>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ name }),
    })
  }

  async deleteSession(id: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/api/sessions/${id}`, {
      method: 'DELETE',
    })
  }

  // Artifact management
  async downloadArtifact(executionId: string, artifactId: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseURL}/api/execute/${executionId}/artifacts/${artifactId}/download`
    )

    if (!response.ok) {
      throw new APIError(response.status, 'Failed to download artifact')
    }

    return response.blob()
  }

  async downloadAllArtifacts(executionId: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseURL}/api/execute/${executionId}/artifacts/download-all`
    )

    if (!response.ok) {
      throw new APIError(response.status, 'Failed to download artifacts')
    }

    return response.blob()
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request<{ status: string; timestamp: string }>('/api/health')
  }
}

export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: any
  ) {
    super(message)
    this.name = 'APIError'
  }

  get isNetworkError(): boolean {
    return this.status === 0
  }

  get isServerError(): boolean {
    return this.status >= 500
  }

  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500
  }
}

// Singleton instance
export const apiClient = new APIClient()

// Helper functions for common patterns
export async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  delayMs: number = 1000
): Promise<T> {
  let lastError: Error

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error as Error

      if (attempt === maxAttempts) {
        throw lastError
      }

      // Don't retry on client errors (4xx)
      if (error instanceof APIError && error.isClientError) {
        throw error
      }

      await new Promise(resolve => setTimeout(resolve, delayMs * attempt))
    }
  }

  throw lastError!
}

export function isAPIError(error: unknown): error is APIError {
  return error instanceof APIError
}