import { render, screen } from '../test/testUtils'
import { ManageDataPanel } from './ManageDataPanel'

// Mock useUploadHL7
jest.mock('../hooks/useUploadHL7', () => ({
  useUploadHL7: () => ({
    upload: jest.fn(),
    isUploading: false,
    uploadResult: null,
    uploadError: null,
    uploadProgress: 0,
    reset: jest.fn(),
  }),
}))

describe('ManageDataPanel', () => {
  it('renders for users with coder role', () => {
    render(<ManageDataPanel userRoles={['coder']} />)

    expect(screen.getByText('Manage Data')).toBeInTheDocument()
    expect(
      screen.getByText(/Upload HL7 message files to import patient encounters/)
    ).toBeInTheDocument()
  })

  it('renders for users with admin role', () => {
    render(<ManageDataPanel userRoles={['admin']} />)

    expect(screen.getByText('Manage Data')).toBeInTheDocument()
  })

  it('renders for users with both coder and admin roles', () => {
    render(<ManageDataPanel userRoles={['coder', 'admin']} />)

    expect(screen.getByText('Manage Data')).toBeInTheDocument()
  })

  it('does not render for users without coder/admin role', () => {
    const { container } = render(<ManageDataPanel userRoles={['viewer']} />)

    expect(container.firstChild).toBeNull()
  })

  it('does not render for users with empty roles', () => {
    const { container } = render(<ManageDataPanel userRoles={[]} />)

    expect(container.firstChild).toBeNull()
  })

  it('shows file upload area', () => {
    render(<ManageDataPanel userRoles={['coder']} />)

    expect(screen.getByText('Click to upload')).toBeInTheDocument()
    expect(screen.getByText('or drag and drop')).toBeInTheDocument()
  })

  it('shows upload button disabled when no files selected', () => {
    render(<ManageDataPanel userRoles={['coder']} />)

    const uploadButton = screen.getByRole('button', { name: /Upload Files/i })
    expect(uploadButton).toBeDisabled()
  })

  it('shows file type hint', () => {
    render(<ManageDataPanel userRoles={['coder']} />)

    expect(screen.getByText('HL7 files (.hl7 or .txt)')).toBeInTheDocument()
  })
})

describe('ManageDataPanel - case insensitive role check', () => {
  it('handles uppercase CODER role', () => {
    render(<ManageDataPanel userRoles={['CODER']} />)

    expect(screen.getByText('Manage Data')).toBeInTheDocument()
  })

  it('handles mixed case Admin role', () => {
    render(<ManageDataPanel userRoles={['Admin']} />)

    expect(screen.getByText('Manage Data')).toBeInTheDocument()
  })
})
