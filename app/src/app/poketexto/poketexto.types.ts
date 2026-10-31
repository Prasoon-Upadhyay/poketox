import type { GuessResult } from '../common/types/api.types'
export type GuessHistoryItem = GuessResult & { submittedAt: number }
