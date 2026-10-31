export interface MenuGame { title: string; subtitle: string; accent: string; motif: string; enabled: boolean }

export type PoketextoMode = 'daily' | 'unlimited'

export interface PoketextoConfig {
  mode: PoketextoMode
  generations: number[]
}
