export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface ChatAskRequest {
  sessionId: string
  text: string
  inputType: 'voice' | 'text'
  preference?: string[]
  poiId?: string
}

export interface SourceItem {
  docId: string
  title: string
  snippet: string
}

export interface PhonemeItem {
  phone: string
  startMs: number
  endMs: number
}

export interface TtsPayload {
  audioUrl: string
  durationMs: number
  phonemes: PhonemeItem[]
}

export interface AvatarPayload {
  expression: string
  gesture: string
}

export interface AvatarStreamPayload {
  sessionId: string
  streamUrl: string
}

export interface ChatAskData {
  messageId: string
  answerText: string
  emotionTag: string
  confidence: number
  sources: SourceItem[]
  tts: TtsPayload
  avatar: AvatarPayload
}

export interface AsrRecognizeData {
  text: string
  confidence: number
  durationMs: number
}

export type MessageRole = 'user' | 'bot'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: number
  emotionTag?: string
  confidence?: number
  sources?: SourceItem[]
}
