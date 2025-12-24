import { render, screen } from '../test/testUtils'
import CodePage from './CodePage'

// Mock useAuth
jest.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    user: { full_name: 'Test User', roles: ['coder'] },
    logout: jest.fn(),
  }),
}))

// Mock useEncounters with data
jest.mock('../hooks/useEncounters', () => ({
  useEncounters: () => ({
    data: {
      encounters: [
        {
          id: '1',
          visit_number: 'V001',
          encounter_type: 'inpatient',
          patient: {
            name_given: 'John',
            name_family: 'Doe',
            mrn: 'MRN001',
          },
        },
        {
          id: '2',
          visit_number: 'V002',
          encounter_type: 'outpatient',
          patient: {
            name_given: 'Jane',
            name_family: 'Smith',
            mrn: 'MRN002',
          },
        },
      ],
      total: 2,
      skip: 0,
      limit: 100,
    },
    isLoading: false,
    error: null,
  }),
}))

describe('CodePage', () => {
  it('renders encounters table with correct columns', () => {
    render(<CodePage />)

    expect(screen.getByText('First Name')).toBeInTheDocument()
    expect(screen.getByText('Last Name')).toBeInTheDocument()
    expect(screen.getByText('Encounter ID')).toBeInTheDocument()
    expect(screen.getByText('Encounter Type')).toBeInTheDocument()
  })

  it('displays encounter data correctly', () => {
    render(<CodePage />)

    expect(screen.getByText('John')).toBeInTheDocument()
    expect(screen.getByText('Doe')).toBeInTheDocument()
    expect(screen.getByText('V001')).toBeInTheDocument()
    expect(screen.getByText('inpatient')).toBeInTheDocument()

    expect(screen.getByText('Jane')).toBeInTheDocument()
    expect(screen.getByText('Smith')).toBeInTheDocument()
    expect(screen.getByText('V002')).toBeInTheDocument()
    expect(screen.getByText('outpatient')).toBeInTheDocument()
  })

  it('shows the Encounters heading', () => {
    render(<CodePage />)

    expect(screen.getByText('Encounters')).toBeInTheDocument()
  })

  it('shows record count', () => {
    render(<CodePage />)

    expect(screen.getByText('Showing 2 of 2 encounters')).toBeInTheDocument()
  })

  it('has back link to dashboard', () => {
    render(<CodePage />)

    const backLink = screen.getByRole('link')
    expect(backLink).toHaveAttribute('href', '/dashboard')
  })
})

// Note: Testing loading/empty states requires a different approach
// due to Jest module caching. The main tests above verify the core functionality
// with a populated data set.
