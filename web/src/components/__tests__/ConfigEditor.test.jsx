import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConfigEditor from '../ConfigEditor';

describe('ConfigEditor', () => {
  const defaultProps = {
    filename: 'server.properties',
    content: '# Test config\nkey=value\n',
    onSave: vi.fn(),
    onCancel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders filename in toolbar', () => {
    render(<ConfigEditor {...defaultProps} />);
    expect(screen.getByText('server.properties')).toBeInTheDocument();
  });

  it('displays initial content', () => {
    render(<ConfigEditor {...defaultProps} />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue('# Test config\nkey=value\n');
  });

  it('shows modified indicator when content changes', async () => {
    render(<ConfigEditor {...defaultProps} />);
    const textarea = screen.getByRole('textbox');

    fireEvent.change(textarea, { target: { value: '# Modified config\nkey=newvalue\n' } });

    await waitFor(() => {
      // There may be multiple "MODIFIED" elements, so use getAllByText
      const modifiedElements = screen.getAllByText(/modified/i);
      expect(modifiedElements.length).toBeGreaterThan(0);
    });
  });

  it('calls onSave when save button is clicked', async () => {
    const onSave = vi.fn().mockResolvedValue({ success: true });
    render(<ConfigEditor {...defaultProps} onSave={onSave} />);

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '# Modified\nkey=new\n' } });

    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith('# Modified\nkey=new\n');
    });
  });

  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn();
    render(<ConfigEditor {...defaultProps} onCancel={onCancel} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(onCancel).toHaveBeenCalled();
  });

  it('disables save button when not modified', () => {
    render(<ConfigEditor {...defaultProps} />);
    const saveButton = screen.getByRole('button', { name: /save/i });
    expect(saveButton).toBeDisabled();
  });

  it('shows error message when save fails', async () => {
    const onSave = vi.fn().mockRejectedValue(new Error('Save failed'));
    render(<ConfigEditor {...defaultProps} onSave={onSave} />);

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '# Modified\n' } });

    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/Save failed/i)).toBeInTheDocument();
    });
  });

  it('displays line count in footer', () => {
    render(<ConfigEditor {...defaultProps} />);
    // Content has 2 lines plus empty line at end = 3 lines total
    expect(screen.getByText(/3\s+lines/i)).toBeInTheDocument();
  });

  it('detects language from filename', () => {
    const { rerender } = render(<ConfigEditor {...defaultProps} filename="server.properties" />);
    // Check for language in footer (more specific than filename)
    expect(screen.getByText(/Language:\s*properties/i)).toBeInTheDocument();

    rerender(<ConfigEditor {...defaultProps} filename="docker-compose.yml" />);
    expect(screen.getByText(/yaml/i)).toBeInTheDocument();
  });
});
