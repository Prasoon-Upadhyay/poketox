import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../common/api/api-client'
import type { DailyGame, EntitySuggestion, GiveUpResult, GuessResult } from '../common/types/api.types'
export const usePoketextoGame = () => useQuery({ queryKey:['poketexto','game'], queryFn:async()=> (await apiClient.get<DailyGame>('/api/v1/daily')).data })
export const usePoketextoSuggestions = (q:string) => useQuery({ queryKey:['poketexto','suggestions',q], queryFn:async()=> (await apiClient.get<EntitySuggestion[]>('/api/v1/entities/suggestions',{params:{q}})).data, enabled:q.length>0, staleTime:30_000 })
export function usePoketextoGuess() { const query=useMutation({mutationFn:async (guess:EntitySuggestion)=> (await apiClient.post<GuessResult>('/api/v1/daily/guesses',guess)).data}); return {...query,isFetching:query.isPending} }
export function usePoketextoReset() { const client=useQueryClient(); return useMutation({mutationFn:async()=> (await apiClient.post<DailyGame>('/api/v1/daily/reset')).data,onSuccess:()=>client.invalidateQueries({queryKey:['poketexto','game']})}) }
export const usePoketextoGiveUp = () => useMutation({mutationFn:async()=> (await apiClient.post<GiveUpResult>('/api/v1/daily/give-up')).data})
