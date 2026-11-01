import { useState } from 'react'
import { PokemonSprite } from '../common/components/pokemon-sprite.component'
import { AbilityIcon } from '../common/components/ability-icon.component'
import { DamageClassIcon } from '../common/components/damage-class-icon.component'
import { showToast } from '../common/components/toast-host.component'
import { TypeBadge } from '../common/components/type-badge.component'
import { useDebouncedValue } from '../common/hooks/use-debounced-value.hook'
import type { EntitySuggestion } from '../common/types/api.types'
import type { PoketextoConfig } from '../menu/menu.types'
import { rankClass, rankFill } from './poketexto.data'
import { usePoketextoGame, usePoketextoGiveUp, usePoketextoGuess, usePoketextoReset, usePoketextoSuggestions } from './poketexto.api'
import type { GuessHistoryItem } from './poketexto.types'

export function Poketexto({ config, onExit }: { config: PoketextoConfig; onExit: () => void }) {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<GuessHistoryItem[]>([])
  const game = usePoketextoGame(config.generations)
  const suggestions = usePoketextoSuggestions(useDebouncedValue(input))
  const guess = usePoketextoGuess()
  const reset = usePoketextoReset()
  const giveUp = usePoketextoGiveUp()
  const solvedGuess = history.find((item) => item.solved)
  const isFinished = Boolean(solvedGuess)

  if (game.isLoading) return <main className="grid min-h-screen place-items-center bg-[#e7eadc] px-4 text-center text-xs font-bold">LOADING POKEDEX...</main>
  if (game.isError || !game.data) return <main className="grid min-h-screen place-items-center bg-[#e7eadc] px-4 text-center"><button onClick={onExit}>API NOT REACHABLE - BACK</button></main>

  const choose = (item: EntitySuggestion) => {
    if (isFinished) return
    setInput('')
    if (history.some((previous) => previous.guess.id === item.id)) {
      showToast(`YOU'VE ALREADY GUESSED ${item.name.toUpperCase()}.`)
      return
    }
    guess.mutate(item, { onSuccess: (data) => setHistory((old) => [{ ...data, submittedAt: Date.now() }, ...old]) })
  }

  return <main className="min-h-screen bg-[#e7eadc] px-3 py-4 sm:py-5"><section className="mx-auto max-w-2xl"><header className="mb-5 flex flex-col gap-4 text-[9px] font-bold sm:mb-7 sm:flex-row sm:items-center sm:justify-between sm:text-xs"><button onClick={onExit} className="min-h-9 self-start">← MENU</button><span className="break-words sm:text-right">POKÉTEXTO / {config.mode.toUpperCase()} / GEN {config.generations.join('-')}</span></header><div className="border-4 border-[#172226] bg-[#f4f0dc] p-3 shadow-[5px_5px_0_#172226] sm:p-6 sm:shadow-[7px_7px_0_#172226]"><h1 className="text-center text-2xl font-black leading-tight sm:text-5xl">WHO'S THAT POKEMON?</h1><div className="mx-auto mt-5 grid size-28 place-items-center overflow-hidden border-3 border-[#172226] bg-[#dbe6ca] shadow-[4px_4px_0_#172226] sm:size-36">{solvedGuess ? <PokemonSprite spriteId={solvedGuess.guess.sprite_id} name={solvedGuess.guess.name} className="m-0 size-full p-1" /> : <span className="text-6xl font-black sm:text-7xl">?</span>}</div><p className="mt-4 min-h-9 text-center text-[9px] leading-5 sm:min-h-4 sm:text-xs">{isFinished ? `YOU FOUND ${solvedGuess?.guess.name.toUpperCase()}!` : 'Choose an item from the dropdown. Lower rank is closer.'}</p><div className="relative mt-5 sm:mt-7"><input disabled={isFinished} value={input} onChange={(event) => setInput(event.target.value)} placeholder="Search a valid guess..." className="min-h-12 w-full border-3 border-[#172226] bg-white p-3 text-[11px] font-bold outline-none disabled:cursor-not-allowed disabled:bg-[#d5d8d0] sm:p-4 sm:text-base" />{input && !isFinished && <div className="absolute z-20 mt-2 max-h-[18.75rem] w-full overflow-y-auto border-3 border-[#172226] bg-[#f4f0dc]">{suggestions.isFetching ? <p className="p-4 text-[10px]">SEARCHING...</p> : suggestions.data?.length ? suggestions.data.map((item) => <SuggestionRow key={item.id} item={item} onClick={choose} />) : <p className="p-4 text-[10px] leading-5">NO ELIGIBLE GUESSES FOUND.</p>}</div>}</div><div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-center"><button onClick={() => reset.mutate({ generations: config.generations }, { onSuccess: () => { setHistory([]); setInput('') } })} className="min-h-11 border-2 border-[#172226] bg-[#cce5a2] px-3 py-2 text-[10px] font-bold">NEW GAME</button><button disabled={isFinished} onClick={() => giveUp.mutate()} className="min-h-11 border-2 border-[#172226] bg-[#f1b466] px-3 py-2 text-[10px] font-bold disabled:opacity-50">GIVE UP</button></div><div className="mt-4 min-h-14">{giveUp.data && <p className="border-2 border-[#172226] bg-[#f6d66a] p-3 text-center text-[10px] font-bold break-words">TARGET: {giveUp.data.target.name}</p>}</div></div><h2 className="mt-8 text-sm font-black sm:mt-9">YOUR GUESSES</h2><div className="mt-3 space-y-2">{history.map((item) => <GuessBar key={`${item.guess.id}-${item.submittedAt}`} item={item} />)}</div></section></main>
}

function GuessBar({ item }: { item: GuessHistoryItem }) { const fill = rankFill(item.rank); return <article className={`relative overflow-hidden border-3 p-3 ${rankClass(item.rank)}`}><span className="absolute inset-y-0 left-0 opacity-80" style={{ width: `${fill.width}%`, backgroundColor: fill.colour }} /><div className="relative flex min-w-0 items-center gap-2 text-[10px] sm:gap-3 sm:text-base"><b className="shrink-0">#{item.rank}</b><b className="truncate uppercase">{item.guess.name}</b></div></article> }

function SuggestionRow({ item, onClick }: { item: EntitySuggestion; onClick: (item: EntitySuggestion) => void }) { return <button onClick={() => onClick(item)} className="flex min-h-14 w-full min-w-0 items-center gap-2 border-b border-[#bec8b7] p-2 text-left hover:bg-[#dce9c7] sm:gap-3 sm:p-3">{item.category === 'pokemon' && <><span className="flex shrink-0 gap-1">{item.types.map((type) => <TypeBadge key={type} type={type} />)}</span><b className="min-w-0 flex-1 truncate text-[10px] uppercase sm:text-base">{item.name}</b><span className="shrink-0"><PokemonSprite spriteId={item.sprite_id} name={item.name} /></span></>}{item.category === 'move' && <><span className="shrink-0"><TypeBadge type={item.move_type ?? 'normal'} /></span><span className="shrink-0"><DamageClassIcon damageClass={item.damage_class} /></span><b className="min-w-0 truncate text-[10px] uppercase sm:text-base">{item.name}</b></>}{item.category === 'type' && <><span className="shrink-0"><TypeBadge type={item.name} /></span><b className="min-w-0 truncate text-[10px] uppercase sm:text-base">{item.name}</b></>}{item.category === 'ability' && <><span className="shrink-0"><AbilityIcon /></span><b className="min-w-0 truncate text-[10px] uppercase sm:text-base">{item.name}</b></>}</button> }
