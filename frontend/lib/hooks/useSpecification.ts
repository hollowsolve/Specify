import { useState, useCallback } from 'react'
import { apiClient, APIError } from '@/lib/api/client'
import { SpecificationRequest, SpecificationResult, SpecificationState } from '@/types'
import { useWebSocket } from './useWebSocket'

export function useSpecification() {
  const [state, setState] = useState<SpecificationState>({
    isGenerating: false,
    progress: 0,
  })

  const { subscribe } = useWebSocket()

  const generateSpecification = useCallback(async (request: SpecificationRequest) => {
    setState(prev => ({
      ...prev,
      isGenerating: true,
      progress: 0,
      error: undefined,
    }))

    try {
      // Subscribe to real-time updates
      subscribe(`spec-${request.analysisId}`, {
        specification_progress: (data) => {
          setState(prev => ({
            ...prev,
            progress: data.progress,
          }))
        },
        error: (data) => {
          setState(prev => ({
            ...prev,
            error: data.error,
            isGenerating: false,
          }))
        },
      })

      const result = await apiClient.generateSpecification(request)

      setState(prev => ({
        ...prev,
        result,
        isGenerating: false,
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
        isGenerating: false,
        progress: 0,
      }))

      throw error
    }
  }, [subscribe])

  const getSpecification = useCallback(async (id: string) => {
    try {
      const result = await apiClient.getSpecification(id)
      setState(prev => ({
        ...prev,
        result,
      }))
      return result
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'Failed to fetch specification'

      setState(prev => ({
        ...prev,
        error: errorMessage,
      }))

      throw error
    }
  }, [])

  const clearError = useCallback(() => {
    setState(prev => ({
      ...prev,
      error: undefined,
    }))
  }, [])

  const reset = useCallback(() => {
    setState({
      isGenerating: false,
      progress: 0,
    })
  }, [])

  return {
    ...state,
    generateSpecification,
    getSpecification,
    clearError,
    reset,
  }
}