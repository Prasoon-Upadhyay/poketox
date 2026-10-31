import { useState } from 'react'
import { Menu } from './menu/menu.component'
import { Poketexto } from './poketexto/poketexto.component'
import { ToastHost } from './common/components/toast-host.component'
export function App(){const [page,setPage]=useState<'menu'|'poketexto'>('menu');return <><ToastHost />{page==='menu'?<Menu onSelectPoketexto={()=>setPage('poketexto')}/>:<Poketexto onExit={()=>setPage('menu')}/>}</>}
