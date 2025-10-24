import { useState, useCallback } from 'react'
import { apiClient, APIError } from '@/lib/api/client'
import { RefinementRequest, RefinementResult, RefinementState, RefinementSuggestion } from '@/types'
import { useWebSocket } from './useWebSocket'

export function useRefinement() {
  const [state, setState] = useState<RefinementState>({
    suggestions: [],
    isRefining: false,
    progress: 0,
  })

  const { subscribe } = useWebSocket()

  const refineSpecification = useCallback(async (request: RefinementRequest) => {
    setState(prev => ({
      ...prev,
      isRefining: true,
      progress: 0,
      error: undefined,
    }))

    try {
      // Subscribe to real-time updates
      subscribe(`refinement-${request.specificationId}`, {
        refinement_progress: (data: any) => {
          setState(prev => ({
            ...prev,
            progress: data.progress,
          }))
        },
        error: (data: any) => {
          setState(prev => ({
            ...prev,
            error: data.error,
            isRefining: false,
          }))
        },
      })

      const result = await apiClient.refineSpecification(request)

      setState(prev => ({
        ...prev,
        result,
        isRefining: false,
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
        isRefining: false,
        progress: 0,
      }))

      throw error
    }
  }, [subscribe])

  const getRefinement = useCallback(async (id: string) => {
    try {
      const result = await apiClient.getRefinement(id)
      setState(prev => ({
        ...prev,
        result,
      }))
      return result
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'Failed to fetch refinement'

      setState(prev => ({
        ...prev,
        error: errorMessage,
      }))

      throw error
    }
  }, [])

  const updateSuggestions = useCallback((suggestions: RefinementSuggestion[]) => {
    setState(prev => ({
      ...prev,
      suggestions,
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
      suggestions: [],
      isRefining: false,
      progress: 0,
    })
  }, [])

  return {
    ...state,
    refineSpecification,
    getRefinement,
    updateSuggestions,
    clearError,
    reset,
  }
}