// Core API Types
export interface AnalysisRequest {
  prompt: string
  userId?: string
  sessionId?: string
}

export interface AnalysisResult {
  id: string
  sessionId: string
  intent: string
  requirements: string[]
  assumptions: string[]
  ambiguities: Ambiguity[]
  timestamp: string
  confidence: number
}

export interface Ambiguity {
  id: string
  description: string
  suggestions: string[]
  severity: 'high' | 'medium' | 'low'
  context: string
}

export interface SpecificationRequest {
  analysisId: string
  additionalContext?: string
}

export interface SpecificationResult {
  id: string
  analysisId: string
  edgeCases: EdgeCase[]
  contradictions: Contradiction[]
  completenessGaps: CompletenessGap[]
  compressedRequirements: string[]
  timestamp: string
  confidence: number
}

export interface EdgeCase {
  id: string
  description: string
  suggestedHandling: string
  severity: 'high' | 'medium' | 'low'
  confidence: number
  category: string
}

export interface Contradiction {
  id: string
  description: string
  conflictingRequirements: string[]
  suggestedResolution: string
  severity: 'high' | 'medium' | 'low'
}

export interface CompletenessGap {
  id: string
  description: string
  missingAspects: string[]
  suggestedAdditions: string[]
  importance: 'high' | 'medium' | 'low'
}

export interface RefinementRequest {
  specificationId: string
  suggestions: RefinementSuggestion[]
}

export interface RefinementSuggestion {
  id: string
  type: 'edge_case' | 'contradiction' | 'completeness'
  action: 'approve' | 'reject' | 'modify'
  originalText: string
  modifiedText?: string
  reasoning?: string
}

export interface RefinementResult {
  id: string
  specificationId: string
  finalSpecification: string
  appliedSuggestions: RefinementSuggestion[]
  timestamp: string
}

export interface ExecutionRequest {
  refinementId: string
  config?: ExecutionConfig
}

export interface ExecutionConfig {
  language?: string
  framework?: string
  architecture?: string
  testingLevel?: 'unit' | 'integration' | 'e2e' | 'all'
  documentation?: boolean
}

export interface ExecutionResult {
  id: string
  refinementId: string
  status: ExecutionStatus
  dag: ExecutionDAG
  agents: AgentStatus[]
  artifacts: Artifact[]
  progress: number
  startTime: string
  endTime?: string
  logs: ExecutionLog[]
}

export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface ExecutionDAG {
  nodes: DAGNode[]
  edges: DAGEdge[]
  criticalPath: string[]
}

export interface DAGNode {
  id: string
  type: 'task' | 'agent' | 'artifact'
  label: string
  status: ExecutionStatus
  progress: number
  startTime?: string
  endTime?: string
  dependencies: string[]
  estimatedDuration?: number
  actualDuration?: number
}

export interface DAGEdge {
  id: string
  source: string
  target: string
  type: 'dependency' | 'data_flow' | 'control_flow'
  label?: string
}

export interface AgentStatus {
  id: string
  type: string
  name: string
  status: ExecutionStatus
  currentTask?: string
  progress: number
  startTime?: string
  timeElapsed: number
  outputPreview?: string
  capabilities: string[]
  queuedTasks: string[]
}

export interface Artifact {
  id: string
  name: string
  type: 'code' | 'documentation' | 'test' | 'config' | 'asset'
  path: string
  content: string
  language?: string
  size: number
  checksum: string
  createdBy: string
  createdAt: string
  modifiedAt: string
}

export interface ExecutionLog {
  id: string
  timestamp: string
  level: 'debug' | 'info' | 'warn' | 'error'
  source: string
  message: string
  metadata?: Record<string, any>
}

// WebSocket Event Types
export interface WebSocketMessage {
  type: string
  payload: any
  timestamp: string
  sessionId?: string
}

export interface AnalysisProgressEvent {
  type: 'analysis_progress'
  payload: {
    sessionId: string
    stage: string
    progress: number
    message: string
  }
}

export interface SpecificationProgressEvent {
  type: 'specification_progress'
  payload: {
    specificationId: string
    stage: string
    progress: number
    message: string
  }
}

export interface ExecutionProgressEvent {
  type: 'execution_progress'
  payload: {
    executionId: string
    nodeId: string
    progress: number
    status: ExecutionStatus
    message: string
  }
}

export interface AgentStatusEvent {
  type: 'agent_status'
  payload: {
    executionId: string
    agentId: string
    status: ExecutionStatus
    currentTask?: string
    progress: number
    message: string
  }
}

export interface ArtifactCreatedEvent {
  type: 'artifact_created'
  payload: {
    executionId: string
    artifact: Artifact
  }
}

export interface ErrorEvent {
  type: 'error'
  payload: {
    sessionId?: string
    error: string
    details?: string
    stage?: string
  }
}

// UI State Types
export interface Session {
  id: string
  name: string
  status: 'active' | 'completed' | 'failed'
  createdAt: string
  lastActivity: string
  phase: 'analyze' | 'specify' | 'refine' | 'execute'
  analysisId?: string
  specificationId?: string
  refinementId?: string
  executionId?: string
}

export interface UIState {
  currentSession?: Session
  sessions: Session[]
  isLoading: boolean
  error?: string
  darkMode: boolean
  sidebarCollapsed: boolean
}

export interface AnalysisState {
  prompt: string
  isAnalyzing: boolean
  result?: AnalysisResult
  progress: number
  error?: string
}

export interface SpecificationState {
  isGenerating: boolean
  result?: SpecificationResult
  progress: number
  error?: string
}

export interface RefinementState {
  suggestions: RefinementSuggestion[]
  isRefining: boolean
  result?: RefinementResult
  progress: number
  error?: string
}

export interface ExecutionState {
  isExecuting: boolean
  result?: ExecutionResult
  progress: number
  error?: string
  selectedNodeId?: string
  viewMode: 'dag' | 'agents' | 'artifacts' | 'logs'
}

// Component Props Types
export interface BaseComponentProps {
  className?: string
  children?: React.ReactNode
}

export interface LoadingState {
  isLoading: boolean
  message?: string
  progress?: number
}

export interface ErrorState {
  error: string
  details?: string
  onRetry?: () => void
  onDismiss?: () => void
}

// Utility Types
export type Severity = 'high' | 'medium' | 'low'
export type Phase = 'analyze' | 'specify' | 'refine' | 'execute'
export type ViewMode = 'dag' | 'agents' | 'artifacts' | 'logs'

export interface PaginationInfo {
  page: number
  limit: number
  total: number
  hasNext: boolean
  hasPrev: boolean
}

export interface SearchFilters {
  query?: string
  type?: string
  severity?: Severity
  status?: ExecutionStatus
  dateRange?: {
    start: string
    end: string
  }
}

export interface ThemeConfig {
  theme: 'light' | 'dark' | 'system'
  primaryColor: string
  borderRadius: number
  fontFamily: string
}

export interface FeatureFlags {
  realTimeUpdates: boolean
  darkMode: boolean
  advancedEditor: boolean
  exportFeatures: boolean
  collaborativeEditing: boolean
}