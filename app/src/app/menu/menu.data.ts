import type { MenuGame } from './menu.types'
export const MENU_GAMES: MenuGame[] = [
  { title:'Pokétexto', subtitle:'Find today’s Pokémon by rank', accent:'from-[#d9e86c] to-[#80b649]', motif:'◉', enabled:true },
  { title:'Type Battle', subtitle:'Head-to-head type deduction', accent:'from-[#e8897c] to-[#bd4e64]', motif:'⚔', enabled:false },
  { title:'Dex Guess', subtitle:'Guess the Pokédex entry', accent:'from-[#8db5e8] to-[#5869b5]', motif:'▦', enabled:false },
  { title:'PokéChain', subtitle:'Link Pokémon together', accent:'from-[#bfa1dc] to-[#7566a7]', motif:'∞', enabled:false },
]
