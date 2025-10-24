import { useState, useCallback } from 'react'
import { apiClient, APIError } from '@/lib/api/client'
import { ExecutionRequest, ExecutionResult, ExecutionState } from '@/types'
import { useWebSocket } from './useWebSocket'

export function useExecution() {
  const [state, setState] = useState<ExecutionState>({
    isExecuting: false,
    progress: 0,
    viewMode: 'dag',
  })

  const { subscribe } = useWebSocket()

  const executeSpecification = useCallback(async (request: ExecutionRequest) => {
    setState(prev => ({
      ...prev,
      isExecuting: true,
      progress: 0,
      error: undefined,
    }))

    try {
      const result = await apiClient.executeSpecification(request)

      // Subscribe to real-time updates
      subscribe(`exec-${result.id}`, {
        execution_progress: (data) => {
          setState(prev => {
            if (prev.result) {
              // Update specific node progress
              const updatedResult = {
                ...prev.result,
                dag: {
                  ...prev.result.dag,
                  nodes: prev.result.dag.nodes.map(node =>
                    node.id === data.nodeId
                      ? { ...node, progress: data.progress, status: data.status }
                      : node
                  ),
                },
                progress: calculateOverallProgress(prev.result.dag.nodes, data.nodeId, data.progress),
              }

              return {
                ...prev,
                result: updatedResult,
                progress: updatedResult.progress,
              }
            }
            return prev
          })
        },
        agent_status: (data) => {
          setState(prev => {
            if (prev.result) {
              const updatedResult = {
                ...prev.result,
                agents: prev.result.agents.map(agent =>
                  agent.id === data.agentId
                    ? {
                        ...agent,
                        status: data.status,
                        currentTask: data.currentTask,
                        progress: data.progress,
                        timeElapsed: Date.now() - (agent.startTime ? new Date(agent.startTime).getTime() : 0),
                      }
                    : agent
                ),
              }

              return {
                ...prev,
                result: updatedResult,
              }
            }
            return prev
          })
        },
        artifact_created: (data) => {
          setState(prev => {
            if (prev.result) {
              const updatedResult = {
                ...prev.result,
                artifacts: [...prev.result.artifacts, data.artifact],
              }

              return {
                ...prev,
                result: updatedResult,
              }
            }
            return prev
          })
        },
        error: (data) => {
          setState(prev => ({
            ...prev,
            error: data.error,
            isExecuting: false,
          }))
        },
      })

      setState(prev => ({
        ...prev,
        result,
        isExecuting: true, // Keep as true since execution is ongoing
      }))

      return result
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'An unexpected error occurred'

      setState(prev => ({
        ...prev,
        error: errorMessage,
        isExecuting: false,
        progress: 0,
      }))

      throw error
    }
  }, [subscribe])

  const getExecution = useCallback(async (id: string) => {
    try {
      const result = await apiClient.getExecution(id)
      setState(prev => ({
        ...prev,
        result,
        isExecuting: result.status === 'running',
        progress: result.progress,
      }))
      return result
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'Failed to fetch execution'

      setState(prev => ({
        ...prev,
        error: errorMessage,
      }))

      throw error
    }
  }, [])

  const stopExecution = useCallback(async (id: string) => {
    try {
      await apiClient.stopExecution(id)
      setState(prev => ({
        ...prev,
        isExecuting: false,
      }))
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'Failed to stop execution'

      setState(prev => ({
        ...prev,
        error: errorMessage,
      }))

      throw error
    }
  }, [])

  const downloadArtifact = useCallback(async (executionId: string, artifactId: string, filename: string) => {
    try {
      const blob = await apiClient.downloadArtifact(executionId, artifactId)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'Failed to download artifact'

      setState(prev => ({
        ...prev,
        error: errorMessage,
      }))

      throw error
    }
  }, [])

  const downloadAllArtifacts = useCallback(async (executionId: string) => {
    try {
      const blob = await apiClient.downloadAllArtifacts(executionId)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = `artifacts-${executionId}.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      const errorMessage = error instanceof APIError
        ? error.message
        : 'Failed to download artifacts'

      setState(prev => ({
        ...prev,
        error: errorMessage,
      }))

      throw error
    }
  }, [])

  const setViewMode = useCallback((viewMode: ExecutionState['viewMode']) => {
    setState(prev => ({
      ...prev,
      viewMode,
    }))
  }, [])

  const selectNode = useCallback((nodeId: string | undefined) => {
    setState(prev => ({
      ...prev,
      selectedNodeId: nodeId,
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
      isExecuting: false,
      progress: 0,
      viewMode: 'dag',
    })
  }, [])

  return {
    ...state,
    executeSpecification,
    getExecution,
    stopExecution,
    downloadArtifact,
    downloadAllArtifacts,
    setViewMode,
    selectNode,
    clearError,
    reset,
  }
}

// Helper function to calculate overall progress
function calculateOverallProgress(
  nodes: any[],
  updatedNodeId: string,
  updatedProgress: number
): number {
  const totalNodes = nodes.length
  if (totalNodes === 0) return 0

  let totalProgress = 0
  for (const node of nodes) {
    if (node.id === updatedNodeId) {
      totalProgress += updatedProgress
    } else {
      totalProgress += node.progress || 0
    }
  }

  return Math.round(totalProgress / totalNodes)
}