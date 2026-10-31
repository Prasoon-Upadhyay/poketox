import { useEffect, useState } from 'react'
export function useDebouncedValue<T>(value: T, delay = 250) { const [output, setOutput] = useState(value); useEffect(() => { const id = setTimeout(() => setOutput(value), delay); return () => clearTimeout(id) }, [value, delay]); return output }
