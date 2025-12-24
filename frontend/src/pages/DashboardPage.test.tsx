import { render, screen } from '../test/testUtils'
import DashboardPage from './DashboardPage'

// Mock useAuth
jest.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    user: { full_name: 'Test User', roles: ['coder'] },
    logout: jest.fn(),
    isAuthenticated: true,
    isLoading: false,
  }),
}))

describe('DashboardPage', () => {
  it('renders Manage Data and Code tiles', () => {
    render(<DashboardPage />)

    expect(screen.getByText('Manage Data')).toBeInTheDocument()
    expect(screen.getByText('Code')).toBeInTheDocument()
  })

  it('renders the dashboard title', () => {
    render(<DashboardPage />)

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('shows user name in nav', () => {
    render(<DashboardPage />)

    expect(screen.getByText('Test User')).toBeInTheDocument()
  })

  it('shows Manage Data tile as enabled for coder role', () => {
    render(<DashboardPage />)

    const manageDataLink = screen.getByRole('link', { name: /Manage Data/i })
    expect(manageDataLink).toHaveAttribute('href', '/manage-data')
  })

  it('shows Code tile as clickable', () => {
    render(<DashboardPage />)

    const codeLink = screen.getByRole('link', { name: /Code/i })
    expect(codeLink).toHaveAttribute('href', '/code')
  })
})

// Note: Testing alternate role states requires a different approach
// due to Jest module caching. The main tests above verify the core functionality.
