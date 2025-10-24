import { useState, useCallback } from 'react'
import { apiClient, APIError } from '@/lib/api/client'
import { wsClient } from '@/lib/websocket/client'
import { AnalysisRequest, AnalysisResult, AnalysisState } from '@/types'
import { useWebSocket } from './useWebSocket'

export function useAnalysis() {
  const [state, setState] = useState<AnalysisState>({
    prompt: '',
    isAnalyzing: false,
    progress: 0,
  })

  const { subscribe, unsubscribe } = useWebSocket()

  const analyzePrompt = useCallback(async (request: AnalysisRequest) => {
    setState(prev => ({
      ...prev,
      isAnalyzing: true,
      progress: 0,
      error: undefined,
    }))

    try {
      // Subscribe to real-time updates
      const sessionId = request.sessionId || Date.now().toString()
      subscribe(sessionId, {
        analysis_progress: (data) => {
          setState(prev => ({
            ...prev,
            progress: data.progress,
          }))
        },
        error: (data) => {
          setState(prev => ({
            ...prev,
            error: data.error,
            isAnalyzing: false,
          }))
        },
      })

      const result = await apiClient.analyzePrompt({
        ...request,
        sessionId,
      })

      setState(prev => ({
        ...prev,
        result,
        isAnalyzing: false,
        progress: 100,
      }))

      return result
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'An unexpected error occurred'

      setState(prev => ({
        ...prev,
        error: errorMessage,
        isAnalyzing: false,
        progress: 0,
      }))

      throw error
    }
  }, [subscribe])

  const getAnalysis = useCallback(async (id: string) => {
    try {
      const result = await apiClient.getAnalysis(id)
      setState(prev => ({
        ...prev,
        result,
      }))
      return result
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'Failed to fetch analysis'

      setState(prev => ({
        ...prev,
        error: errorMessage,
      }))

      throw error
    }
  }, [])

  const updatePrompt = useCallback((prompt: string) => {
    setState(prev => ({
      ...prev,
      prompt,
    }))
  }, [])

  const clearError = useCallback(() => {
    setState(prev => ({
      ...prev,
      error: undefined,
    }))
  }, [])

  const reset = useCallback(() => {
    setState({
      prompt: '',
      isAnalyzing: false,
      progress: 0,
    })
  }, [])

  return {
    ...state,
    analyzePrompt,
    getAnalysis,
    updatePrompt,
    clearError,
    reset,
  }
}