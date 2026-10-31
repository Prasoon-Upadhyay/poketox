export type EntityCategory = 'pokemon' | 'move' | 'ability' | 'type'
export interface EntitySuggestion { id: string; category: EntityCategory; name: string; types: string[]; move_type: string | null; damage_class: 'physical' | 'special' | 'status' | null; power: number | null; sprite_id: number | null }
export interface DailyGame { puzzle_id: string; generations: number[]; categories: EntityCategory[] }
export interface GuessResult { status: 'accepted'; guess: EntitySuggestion; rank: number; solved: boolean }
export interface GiveUpResult { status: 'given_up'; puzzle_id: string; target: EntitySuggestion }
