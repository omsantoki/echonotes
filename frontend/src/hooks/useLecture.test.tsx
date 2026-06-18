import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useLecture } from '@/hooks/useLecture'
import { ApiRequestError } from '@/lib/http'

vi.mock('@/lib/api', () => ({ api: { getLecture: vi.fn() }, auth: {} }))
import { api } from '@/lib/api'

const getLecture = api.getLecture as ReturnType<typeof vi.fn>

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retryDelay: 0 } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

beforeEach(() => vi.clearAllMocks())

describe('useLecture', () => {
  it('returns the ready document', async () => {
    getLecture.mockResolvedValue({ id: '1', status: 'ready', title: 't', document: { topics: [] } })
    const { result } = renderHook(() => useLecture('1'), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.data?.status).toBe('ready'))
  })

  it('does NOT retry a 404 (terminal not-found / not-owned)', async () => {
    getLecture.mockRejectedValue(new ApiRequestError('No lecture', 'lecture_not_found', 404))
    const { result } = renderHook(() => useLecture('x'), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(getLecture).toHaveBeenCalledTimes(1)
  })

  it('retries a transient 5xx once', async () => {
    getLecture.mockRejectedValue(new ApiRequestError('boom', 'internal_error', 500))
    const { result } = renderHook(() => useLecture('x'), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 })
    expect(getLecture).toHaveBeenCalledTimes(2) // initial + one retry
  })
})
