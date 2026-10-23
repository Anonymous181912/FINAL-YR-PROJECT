import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Login from './pages/Login.jsx'
import { AuthProvider } from './auth.jsx'

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('Login page', () => {
  it('renders the sign-in form', () => {
    renderLogin()
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('name@example.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument()
  })

  it('toggles to registration mode with policy hint', () => {
    renderLogin()
    fireEvent.click(screen.getByText('New here? Create an account'))
    expect(screen.getByText('Create your account')).toBeInTheDocument()
    expect(screen.getByText(/Min 8 characters/)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Your full name')).toBeInTheDocument()
  })

  it('shows license field for doctor registration', () => {
    renderLogin()
    fireEvent.click(screen.getByText('New here? Create an account'))
    fireEvent.click(screen.getAllByText('Doctor Portal')[0])
    expect(screen.getByText(/Medical License Number/)).toBeInTheDocument()
  })
})
