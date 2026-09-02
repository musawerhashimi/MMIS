import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useAuth } from '@/stores/auth'
import { useTheme } from '@/stores/theme'
import { AppShell } from '@/components/layout/AppShell'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { LoginPage } from '@/features/auth/LoginPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { MonographListPage } from '@/features/monographs/MonographListPage'
import { MonographDetailPage } from '@/features/monographs/MonographDetailPage'
import { NewMonographPage } from '@/features/monographs/NewMonographPage'
import { FormsPage } from '@/features/monographs/FormsPage'
import { ReviewQueuePage } from '@/features/reviews/ReviewQueuePage'
import { DefenseListPage } from '@/features/defenses/DefenseListPage'
import { DefenseDetailPage } from '@/features/defenses/DefenseDetailPage'
import { ArchivePage } from '@/features/archive/ArchivePage'
import { ReportsPage } from '@/features/reports/ReportsPage'
import { PeoplePage } from '@/features/people/PeoplePage'
import { SettingsPage } from '@/features/settings/SettingsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is pushed over websockets when it changes, so aggressive
      // refetching would only cost bandwidth on a weak connection.
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Never retry a refused request — the answer will not change.
        const status = (error as { response?: { status?: number } }).response?.status
        if (status === 401 || status === 403 || status === 404) return false
        return failureCount < 2
      },
    },
  },
})

export default function App() {
  const restore = useAuth((s) => s.restore)
  const theme = useTheme((s) => s.theme)

  useEffect(() => {
    restore()
  }, [restore])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="monographs" element={<MonographListPage />} />
            <Route path="monographs/new" element={<NewMonographPage />} />
            <Route path="monographs/:id" element={<MonographDetailPage />} />
            <Route path="monographs/:id/forms" element={<FormsPage />} />

            <Route
              path="reviews"
              element={
                <ProtectedRoute allow={(p) => p.can_supervise || p.is_admin}>
                  <ReviewQueuePage />
                </ProtectedRoute>
              }
            />

            <Route path="defenses" element={<DefenseListPage />} />
            <Route path="defenses/:id" element={<DefenseDetailPage />} />
            <Route path="archive" element={<ArchivePage />} />

            <Route
              path="reports"
              element={
                <ProtectedRoute allow={(p) => p.is_head_of_department || p.is_admin}>
                  <ReportsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="people"
              element={
                <ProtectedRoute allow={(p) => p.is_head_of_department || p.is_admin}>
                  <PeoplePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="settings"
              element={
                <ProtectedRoute allow={(p) => p.is_head_of_department || p.is_admin}>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster
        position="top-right"
        theme={theme}
        toastOptions={{
          style: {
            background: 'var(--surface-raised)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
          },
        }}
      />
    </QueryClientProvider>
  )
}
