import { useEffect, useState } from 'react'

export const TOAST_EVENT = 'poketox:toast'

export function showToast(message: string) {
  window.dispatchEvent(new CustomEvent<string>(TOAST_EVENT, { detail: message }))
}

export function ToastHost() {
  const [message, setMessage] = useState('')
  useEffect(() => {
    let timeout = 0
    const receive = (event: Event) => {
      setMessage((event as CustomEvent<string>).detail)
      window.clearTimeout(timeout)
      timeout = window.setTimeout(() => setMessage(''), 3_000)
    }
    window.addEventListener(TOAST_EVENT, receive)
    return () => { window.removeEventListener(TOAST_EVENT, receive); window.clearTimeout(timeout) }
  }, [])
  if (!message) return null
  return <div role="status" className="fixed inset-x-4 bottom-5 z-50 mx-auto max-w-md border-3 border-[#f4f0dc] bg-[#202c40] px-4 py-3 text-center text-[10px] font-bold text-white shadow-[5px_5px_0_#172226]">{message}</div>
}
