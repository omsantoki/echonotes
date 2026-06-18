import { describe, it, expect, beforeEach } from 'vitest'
import { getToken, setToken, clearToken, subscribe } from '@/lib/session'

describe('session', () => {
  beforeEach(() => clearToken())

  it('stores, reads, and clears the token', () => {
    expect(getToken()).toBeNull()
    setToken('jwt-abc')
    expect(getToken()).toBe('jwt-abc')
    clearToken()
    expect(getToken()).toBeNull()
  })

  it('notifies subscribers on set and clear, and stops after unsubscribe', () => {
    let calls = 0
    const unsub = subscribe(() => {
      calls++
    })
    setToken('x')
    clearToken()
    expect(calls).toBe(2)
    unsub()
    setToken('y')
    expect(calls).toBe(2)
  })
})
