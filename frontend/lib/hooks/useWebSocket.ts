import { useEffect, useRef, useCallback } from 'react'
import { wsClient, WebSocketEventType, WebSocketEventHandler } from '@/lib/websocket/client'

export interface WebSocketSubscription {
  [key: string]: WebSocketEventHandler
}

export function useWebSocket() {
  const subscriptionsRef = useRef<Map<string, WebSocketSubscription>>(new Map())

  const subscribe = useCallback((sessionId: string, handlers: WebSocketSubscription) => {
    // Store subscription for cleanup
    subscriptionsRef.current.set(sessionId, handlers)

    // Subscribe to WebSocket events
    Object.entries(handlers).forEach(([event, handler]) => {
      wsClient.on(event as WebSocketEventType, handler)
    })

    // Subscribe to session updates
    wsClient.subscribe(sessionId)

    return () => {
      unsubscribe(sessionId)
    }
  }, [])

  const unsubscribe = useCallback((sessionId: string) => {
    const handlers = subscriptionsRef.current.get(sessionId)

    if (handlers) {
      // Remove WebSocket event listeners
      Object.entries(handlers).forEach(([event, handler]) => {
        wsClient.off(event as WebSocketEventType, handler)
      })

      // Unsubscribe from session updates
      wsClient.unsubscribe(sessionId)

      // Remove from our tracking
      subscriptionsRef.current.delete(sessionId)
    }
  }, [])

  const isConnected = wsClient.isConnected
  const connectionState = wsClient.connectionState

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Clean up all subscriptions
      subscriptionsRef.current.forEach((handlers, sessionId) => {
        unsubscribe(sessionId)
      })
    }
  }, [unsubscribe])

  return {
    subscribe,
    unsubscribe,
    isConnected,
    connectionState,
    connect: () => wsClient.connect(),
    disconnect: () => wsClient.disconnect(),
  }
}