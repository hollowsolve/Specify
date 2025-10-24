import {
  WebSocketMessage,
  AnalysisProgressEvent,
  SpecificationProgressEvent,
  ExecutionProgressEvent,
  AgentStatusEvent,
  ArtifactCreatedEvent,
  ErrorEvent,
} from '@/types'

export type WebSocketEventType =
  | 'analysis_progress'
  | 'specification_progress'
  | 'execution_progress'
  | 'agent_status'
  | 'artifact_created'
  | 'error'
  | 'connected'
  | 'disconnected'
  | 'reconnecting'

export type WebSocketEventHandler<T = any> = (data: T) => void

export interface WebSocketOptions {
  url?: string
  reconnectAttempts?: number
  reconnectInterval?: number
  heartbeatInterval?: number
  debug?: boolean
}

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts: number
  private reconnectInterval: number
  private heartbeatInterval: number
  private debug: boolean
  private currentAttempt = 0
  private reconnectTimer: NodeJS.Timeout | null = null
  private heartbeatTimer: NodeJS.Timeout | null = null
  private eventHandlers = new Map<WebSocketEventType, Set<WebSocketEventHandler>>()
  private isConnecting = false
  private shouldReconnect = true

  constructor(options: WebSocketOptions = {}) {
    this.url = options.url || process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
    this.reconnectAttempts = options.reconnectAttempts || 5
    this.reconnectInterval = options.reconnectInterval || 3000
    this.heartbeatInterval = options.heartbeatInterval || 30000
    this.debug = options.debug || false
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      if (this.isConnecting) {
        reject(new Error('Connection already in progress'))
        return
      }

      this.isConnecting = true
      this.log('Connecting to WebSocket...', this.url)

      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          this.log('WebSocket connected')
          this.isConnecting = false
          this.currentAttempt = 0
          this.startHeartbeat()
          this.emit('connected', null)
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event)
        }

        this.ws.onclose = (event) => {
          this.log('WebSocket closed', event.code, event.reason)
          this.isConnecting = false
          this.stopHeartbeat()
          this.emit('disconnected', { code: event.code, reason: event.reason })

          if (this.shouldReconnect && !event.wasClean) {
            this.scheduleReconnect()
          }
        }

        this.ws.onerror = (error) => {
          this.log('WebSocket error', error)
          this.isConnecting = false

          if (this.currentAttempt === 0) {
            reject(new Error('Failed to connect to WebSocket'))
          }
        }
      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  disconnect(): void {
    this.shouldReconnect = false
    this.stopReconnect()
    this.stopHeartbeat()

    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting')
      this.ws = null
    }
  }

  send(message: any): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message))
        this.log('Sent message', message)
        return true
      } catch (error) {
        this.log('Failed to send message', error)
        return false
      }
    }
    return false
  }

  subscribe(sessionId: string): boolean {
    return this.send({
      type: 'subscribe',
      sessionId,
      timestamp: new Date().toISOString(),
    })
  }

  unsubscribe(sessionId: string): boolean {
    return this.send({
      type: 'unsubscribe',
      sessionId,
      timestamp: new Date().toISOString(),
    })
  }

  on<T = any>(event: WebSocketEventType, handler: WebSocketEventHandler<T>): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler)
  }

  off<T = any>(event: WebSocketEventType, handler: WebSocketEventHandler<T>): void {
    this.eventHandlers.get(event)?.delete(handler)
  }

  private emit<T = any>(event: WebSocketEventType, data: T): void {
    this.eventHandlers.get(event)?.forEach(handler => {
      try {
        handler(data)
      } catch (error) {
        this.log('Error in event handler', error)
      }
    })
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      this.log('Received message', message)

      switch (message.type) {
        case 'analysis_progress':
          this.emit('analysis_progress', message.payload as AnalysisProgressEvent['payload'])
          break

        case 'specification_progress':
          this.emit('specification_progress', message.payload as SpecificationProgressEvent['payload'])
          break

        case 'execution_progress':
          this.emit('execution_progress', message.payload as ExecutionProgressEvent['payload'])
          break

        case 'agent_status':
          this.emit('agent_status', message.payload as AgentStatusEvent['payload'])
          break

        case 'artifact_created':
          this.emit('artifact_created', message.payload as ArtifactCreatedEvent['payload'])
          break

        case 'error':
          this.emit('error', message.payload as ErrorEvent['payload'])
          break

        case 'pong':
          // Heartbeat response
          break

        default:
          this.log('Unknown message type', message.type)
      }
    } catch (error) {
      this.log('Failed to parse message', error, event.data)
    }
  }

  private scheduleReconnect(): void {
    if (this.currentAttempt >= this.reconnectAttempts) {
      this.log('Max reconnection attempts reached')
      return
    }

    this.currentAttempt++
    const delay = this.reconnectInterval * Math.pow(1.5, this.currentAttempt - 1)

    this.log(`Reconnecting in ${delay}ms (attempt ${this.currentAttempt}/${this.reconnectAttempts})`)
    this.emit('reconnecting', { attempt: this.currentAttempt, delay })

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(() => {
        // Error already logged in connect method
      })
    }, delay)
  }

  private stopReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping', timestamp: new Date().toISOString() })
      }
    }, this.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private log(...args: any[]): void {
    if (this.debug) {
      console.log('[WebSocket]', ...args)
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get connectionState(): string {
    if (!this.ws) return 'closed'

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'open'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'closed'
      default:
        return 'unknown'
    }
  }
}

// Singleton instance
export const wsClient = new WebSocketClient({
  debug: process.env.NODE_ENV === 'development',
})

// Auto-connect when module loads (in browser only)
if (typeof window !== 'undefined') {
  wsClient.connect().catch(console.error)

  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    wsClient.disconnect()
  })
}