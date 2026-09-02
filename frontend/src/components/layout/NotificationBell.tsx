import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCheck } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { cn, timeAgo } from '@/lib/utils'
import { useWebSocket } from '@/hooks/useWebSocket'
import { Button } from '@/components/ui/Button'
import type { Notification, Paginated } from '@/types'

/**
 * The bell.
 *
 * Counts arrive over the websocket so a student sees feedback the moment it is
 * written, but the list is still fetched normally — if the socket is down on a
 * weak connection the bell must keep working.
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data: count } = useQuery({
    queryKey: ['notifications', 'count'],
    queryFn: async () => {
      const { data } = await api.get<{ unread_count: number }>('/notifications/unread_count/')
      return data.unread_count
    },
    refetchInterval: 60_000,
  })

  const { data: list } = useQuery({
    queryKey: ['notifications', 'recent'],
    queryFn: async () => {
      const { data } = await api.get<Paginated<Notification>>('/notifications/')
      return data.results
    },
    enabled: open,
  })

  useWebSocket({
    path: '/ws/notifications/',
    onMessage: (raw) => {
      const message = raw as { event: string; data?: Notification; unread_count?: number }
      if (message.event === 'notification' && message.data) {
        toast(message.data.title, { description: message.data.body })
        queryClient.setQueryData(['notifications', 'count'], message.unread_count ?? 0)
        queryClient.invalidateQueries({ queryKey: ['notifications', 'recent'] })
        // A notification almost always means a monograph changed.
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      }
    },
  })

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent) => {
      if (!(event.target as HTMLElement).closest('[data-bell]')) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const unread = count ?? 0

  async function markAllRead() {
    await api.post('/notifications/mark_all_read/')
    queryClient.setQueryData(['notifications', 'count'], 0)
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
  }

  return (
    <div className="relative" data-bell>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text)]"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
      >
        <Bell className="h-4.5 w-4.5" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="animate-in absolute right-0 top-11 z-50 w-80 surface shadow-lg">
          <div className="flex items-center justify-between border-b px-4 py-2.5">
            <p className="text-sm font-semibold">Notifications</p>
            {unread > 0 && (
              <Button variant="ghost" size="sm" onClick={markAllRead} icon={<CheckCheck className="h-3.5 w-3.5" />}>
                Mark all read
              </Button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {!list?.length ? (
              <p className="px-4 py-8 text-center text-xs text-muted">Nothing yet.</p>
            ) : (
              list.map((item) => (
                <Link
                  key={item.id}
                  to={item.link || '#'}
                  onClick={() => setOpen(false)}
                  className={cn(
                    'block border-b px-4 py-3 transition-colors last:border-0 hover:bg-[var(--surface-sunken)]',
                    !item.is_read && 'bg-brand-50/50 dark:bg-brand-950/20',
                  )}
                >
                  <div className="flex items-start gap-2">
                    {!item.is_read && <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />}
                    <div className="min-w-0">
                      <p className="text-xs font-medium leading-snug">{item.title}</p>
                      <p className="mt-0.5 line-clamp-2 text-[11px] text-muted">{item.body}</p>
                      <p className="mt-1 text-[10px] text-subtle">{timeAgo(item.created_at)}</p>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
