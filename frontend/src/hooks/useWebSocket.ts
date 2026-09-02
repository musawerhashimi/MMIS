/**
 * Live updates.
 *
 * The connection is expected to drop — students are on weak mobile signal —
 * so reconnection is automatic and backs off rather than hammering a server
 * that may itself be down.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { tokens } from '@/lib/api'

type Status = 'connecting' | 'open' | 'closed'

interface Options {
  /** Path such as `/ws/notifications/`. Null disables the connection. */
  path: string | null
  onMessage?: (data: unknown) => void
  enabled?: boolean
}

export function useWebSocket({ path, onMessage, enabled = true }: Options) {
  const [status, setStatus] = useState<Status>('closed')
  const socket = useRef<WebSocket | null>(null)
  const attempts = useRef(0)
  const timer = useRef<number | null>(null)
  const closing = useRef(false)

  // Held in a ref so a changing handler does not tear down the socket.
  const handler = useRef(onMessage)
  useEffect(() => {
    handler.current = onMessage
  }, [onMessage])

  const connect = useCallback(() => {
    if (!path || !enabled) return
    const token = tokens.access
    if (!token) return

    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${scheme}://${window.location.host}${path}?token=${token}`

    setStatus('connecting')
    const ws = new WebSocket(url)
    socket.current = ws

    ws.onopen = () => {
      attempts.current = 0
      setStatus('open')
    }

    ws.onmessage = (event) => {
      try {
        handler.current?.(JSON.parse(event.data))
      } catch {
        // A malformed frame is not worth breaking the page over.
      }
    }

    ws.onclose = () => {
      setStatus('closed')
      if (closing.current) return

      // Back off, but keep trying: a student who walks into a signal blackspot
      // should reconnect on their own when they walk out of it.
      const delay = Math.min(1000 * 2 ** attempts.current, 30_000)
      attempts.current += 1
      timer.current = window.setTimeout(connect, delay)
    }

    ws.onerror = () => ws.close()
  }, [path, enabled])

  useEffect(() => {
    closing.current = false
    connect()

    return () => {
      closing.current = true
      if (timer.current) window.clearTimeout(timer.current)
      socket.current?.close()
    }
  }, [connect])

  const send = useCallback((payload: unknown) => {
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify(payload))
    }
  }, [])

  return { status, send }
}
