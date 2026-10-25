import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

const { mockState } = vi.hoisted(() => ({
  mockState: { requestHandlers: [], responseHandlers: [], instance: null, post: null },
}))

vi.mock('axios', () => {
  const instance = vi.fn()
  instance.interceptors = {
    request: { use: (fn) => mockState.requestHandlers.push(fn) },
    response: { use: (ok, err) => mockState.responseHandlers.push({ ok, err }) },
  }
  instance.post = vi.fn()
  instance.mockResolvedValue({ data: { retried: true } })
  mockState.instance = instance
  mockState.post = vi.fn()
  return { default: { create: () => instance, post: mockState.post } }
})

import { createPrescription } from './services/prescriptions.js'

const originalLocation = window.location

function rejectWith(config, status) {
  const handler = mockState.responseHandlers[0].err
  return handler({
    config: { headers: {}, ...config },
    response: { status },
  })
}

function usePortal(pathname = '/doctor/prescriptions') {
  window.location = { pathname, href: '' }
}

describe('api client auth handling', () => {
  beforeEach(() => {
    localStorage.clear()
    usePortal()
    mockState.post.mockReset()
    mockState.instance.post.mockReset()
    mockState.instance.post.mockResolvedValue({ data: { id: 'rx-1' } })
    mockState.instance.mockClear()
  })

  afterEach(() => {
    window.location = originalLocation
    localStorage.clear()
  })

  it('attaches the stored access token to requests', () => {
    localStorage.setItem('access_token', 'token-1')
    const config = mockState.requestHandlers[0]({ headers: {} })
    expect(config.headers.Authorization).toBe('Bearer token-1')
  })

  it('refreshes once, stores the rotated refresh token and retries the request', async () => {
    localStorage.setItem('access_token', 'old')
    localStorage.setItem('refresh_token', 'refresh-1')
    mockState.post.mockResolvedValue({
      data: { access_token: 'new-access', refresh_token: 'refresh-2' },
    })

    const result = await rejectWith({ url: '/prescriptions/' }, 401)

    expect(result).toEqual({ data: { retried: true } })
    expect(mockState.post).toHaveBeenCalledTimes(1)
    expect(mockState.post).toHaveBeenCalledWith('/api/v1/auth/refresh', {
      refresh_token: 'refresh-1',
    })
    expect(localStorage.getItem('access_token')).toBe('new-access')
    expect(localStorage.getItem('refresh_token')).toBe('refresh-2')
    expect(mockState.instance).toHaveBeenCalledTimes(1)
    expect(mockState.instance.mock.calls[0][0].headers.Authorization).toBe('Bearer new-access')
  })

  it('shares one refresh between parallel 401 responses', async () => {
    localStorage.setItem('access_token', 'old')
    localStorage.setItem('refresh_token', 'refresh-1')
    let resolveRefresh
    mockState.post.mockReturnValue(
      new Promise((resolve) => {
        resolveRefresh = resolve
      })
    )

    const first = rejectWith({ url: '/prescriptions/' }, 401)
    const second = rejectWith({ url: '/prescriptions/abc' }, 401)
    await Promise.resolve()
    resolveRefresh({ data: { access_token: 'new-access', refresh_token: 'refresh-2' } })

    await expect(first).resolves.toBeTruthy()
    await expect(second).resolves.toBeTruthy()
    expect(mockState.post).toHaveBeenCalledTimes(1)
    expect(mockState.instance).toHaveBeenCalledTimes(2)
  })

  it('clears the session and redirects to the role portal when refresh fails', async () => {
    localStorage.setItem('access_token', 'old')
    localStorage.setItem('refresh_token', 'refresh-1')
    localStorage.setItem('user', JSON.stringify({ role: 'doctor' }))
    mockState.post.mockRejectedValue(new Error('refresh expired'))

    await expect(rejectWith({ url: '/prescriptions/' }, 401)).rejects.toBeTruthy()

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
    expect(window.location.href).toBe('/doctor/login')
  })

  it('redirects to the patient portal when there is no refresh token', async () => {
    localStorage.setItem('access_token', 'old')
    localStorage.setItem('user', JSON.stringify({ role: 'patient' }))

    await expect(rejectWith({ url: '/prescriptions/' }, 401)).rejects.toBeTruthy()

    expect(mockState.post).not.toHaveBeenCalled()
    expect(window.location.href).toBe('/patient/login')
  })

  it('does not log out or redirect on a 403', async () => {
    localStorage.setItem('access_token', 'still-valid')
    localStorage.setItem('refresh_token', 'refresh-1')
    localStorage.setItem('user', JSON.stringify({ role: 'doctor' }))

    await expect(rejectWith({ url: '/prescriptions/' }, 403)).rejects.toBeTruthy()

    expect(localStorage.getItem('access_token')).toBe('still-valid')
    expect(mockState.post).not.toHaveBeenCalled()
    expect(window.location.href).toBe('')
  })

  it('does not refresh while already on a login page', async () => {
    usePortal('/doctor/login')
    localStorage.setItem('refresh_token', 'refresh-1')

    await expect(rejectWith({ url: '/auth/me' }, 401)).rejects.toBeTruthy()

    expect(mockState.post).not.toHaveBeenCalled()
    expect(window.location.href).toBe('')
  })

  it('creates drafts with the backend trailing-slash URL', async () => {
    await createPrescription({ patient_id: 'p1' })
    expect(mockState.instance.post).toHaveBeenCalledWith('/prescriptions/', { patient_id: 'p1' })
  })
})
