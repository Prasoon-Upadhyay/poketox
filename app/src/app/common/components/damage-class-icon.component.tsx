import type { EntitySuggestion } from '../types/api.types'

export function DamageClassIcon({ damageClass }: { damageClass: EntitySuggestion['damage_class'] }) {
  if (damageClass === 'status') return <span className="grid h-8 w-15 place-items-center border-2 border-[#172226] bg-[#909090] text-[7px] text-white">STATUS</span>
  const special = damageClass === 'special'
  return <span title={special ? 'Special move' : 'Physical move'} className={`grid h-8 w-15 grid-rows-[18px_1fr] border-2 border-[#172226] p-px text-[6px] ${special ? 'bg-[#2d5db9]' : 'bg-[#e08331]'}`}>
    <span className={`grid place-items-center border border-white/70 ${special ? 'bg-[#103d90]' : 'bg-[#ef4825]'}`}>
      {special ? <svg viewBox="0 0 40 20" className="h-4 w-9" aria-hidden="true"><ellipse cx="20" cy="10" rx="13" ry="7" fill="none" stroke="#d8eeff" strokeWidth="2"/><ellipse cx="20" cy="10" rx="7" ry="4" fill="none" stroke="#d8eeff" strokeWidth="2"/><circle cx="20" cy="10" r="2" fill="#d8eeff"/></svg> : <svg viewBox="0 0 40 20" className="h-4 w-9" aria-hidden="true"><path d="M20 1 23 7 30 5 29 11 37 12 31 15 34 19 27 18 25 24 20 19 15 24 13 18 6 19 9 15 3 12 11 11 10 5 17 7Z" transform="translate(0 -3)" fill="#ffd53a"/></svg>}
    </span>
    <span className="grid place-items-center font-bold text-white">{special ? 'SPECIAL' : 'PHYSICAL'}</span>
  </span>
}
