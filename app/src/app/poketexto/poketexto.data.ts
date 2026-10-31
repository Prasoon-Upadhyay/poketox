export function rankClass(rank:number) { return rank === 1 ? 'border-[#f4f0dc] border-l-8 border-l-[#f6d66a] bg-[#202c40] text-white' : rank <= 200 ? 'border-[#f4f0dc] border-l-8 border-l-[#72c35d] bg-[#202c40] text-white' : rank <= 1000 ? 'border-[#f4f0dc] border-l-8 border-l-[#f5822d] bg-[#202c40] text-white' : 'border-[#f4f0dc] border-l-8 border-l-[#e83e8c] bg-[#202c40] text-white' }

export function rankFill(rank: number) {
  const colour = rank === 1 ? '#f6d66a' : rank <= 200 ? '#72c35d' : rank <= 1000 ? '#f5822d' : '#e83e8c'
  return { colour, width: rank === 1 ? 100 : Math.max(3, 100 - Math.min(rank, 3609) / 36.09) }
}
