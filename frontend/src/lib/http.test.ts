import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getJson, postJson, ApiRequestError } from '@/lib/http'
import { setToken, getToken, clearToken } from '@/lib/session'

const fetchMock = vi.fn()

function res(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: '',
    json: async () => body,
  } as Response
}

beforeEach(() => {
  clearToken()
  fetchMock.mockReset()
  global.fetch = fetchMock as unknown as typeof fetch
})

describe('http', () => {
  it('attaches Authorization: Bearer when a session token is set', async () => {
    setToken('jwt-1')
    fetchMock.mockResolvedValue(res(200, { ok: true }))
    await getJson('/api/courses')
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer jwt-1')
  })

  it('omits Authorization when there is no token', async () => {
    fetchMock.mockResolvedValue(res(200, {}))
    await getJson('/api/courses')
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined()
  })

  it('clears the session on a 401 from a data route', async () => {
    setToken('jwt-1')
    fetchMock.mockResolvedValue(res(401, { error: { code: 'unauthorized', message: 'no' } }))
    await expect(getJson('/api/courses')).rejects.toBeInstanceOf(ApiRequestError)
    expect(getToken()).toBeNull()
  })

  it('does NOT clear the session on a 401 from an /api/auth route', async () => {
    setToken('jwt-1')
    fetchMock.mockResolvedValue(res(401, { error: { code: 'invalid_credentials', message: 'bad' } }))
    await expect(postJson('/api/auth/login', {})).rejects.toMatchObject({
      code: 'invalid_credentials',
      status: 401,
    })
    expect(getToken()).toBe('jwt-1')
  })

  it('parses the {error:{code,message}} envelope into ApiRequestError', async () => {
    fetchMock.mockResolvedValue(res(400, { error: { code: 'bad_format', message: 'nope' } }))
    await expect(getJson('/api/x')).rejects.toMatchObject({
      code: 'bad_format',
      message: 'nope',
      status: 400,
    })
  })

  it('returns parsed JSON on success', async () => {
    fetchMock.mockResolvedValue(res(200, { id: '1', name: 'Bio' }))
    await expect(getJson('/api/courses/1')).resolves.toEqual({ id: '1', name: 'Bio' })
  })
})
