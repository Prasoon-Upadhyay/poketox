import { useState } from 'react'
import { Menu } from './menu/menu.component'
import { Poketexto } from './poketexto/poketexto.component'
import { ToastHost } from './common/components/toast-host.component'
import type { PoketextoConfig } from './menu/menu.types'

const DEFAULT_CONFIG: PoketextoConfig = { mode: 'daily', generations: [1, 2, 3, 4, 5] }

export function App(){const [page,setPage]=useState<'menu'|'poketexto'>('menu');const [config,setConfig]=useState<PoketextoConfig>(DEFAULT_CONFIG);return <><ToastHost />{page==='menu'?<Menu onSelectPoketexto={(nextConfig)=>{setConfig(nextConfig);setPage('poketexto')}}/>:<Poketexto config={config} onExit={()=>setPage('menu')}/>}</>}
