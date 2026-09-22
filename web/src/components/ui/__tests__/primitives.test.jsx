import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Alert, ErrorState } from '../Alert';
import { Badge, StatusPill } from '../Badge';
import { Button } from '../Button';
import { Card } from '../Card';
import { Input, Select, Textarea } from '../FormField';
import { Modal } from '../Modal';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../Table';

describe('Button', () => {
  it('renders children and responds to click', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>SAVE</Button>);
    await userEvent.click(screen.getByRole('button', { name: 'SAVE' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled while loading and not clickable', async () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} loading>
        SAVE
      </Button>
    );
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
  });

  it('gives an icon-only button an accessible name via iconLabel', () => {
    render(<Button icon="🗑" iconLabel="Delete" />);
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });
});

describe('Card', () => {
  it('renders children with the base themed class', () => {
    render(<Card data-testid="card">content</Card>);
    const card = screen.getByTestId('card');
    expect(card).toHaveClass('card-minecraft');
    expect(card.className).not.toMatch(/animate-fadeIn/);
  });

  it('opts into the fade-in animation only when asked', () => {
    render(
      <Card data-testid="card" animateIn>
        content
      </Card>
    );
    expect(screen.getByTestId('card')).toHaveClass('animate-fadeIn');
  });
});

describe('FormField (Input/Select/Textarea)', () => {
  it('associates a label with its input via htmlFor/id', () => {
    render(<Input label="Username" />);
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
  });

  it('marks an errored input as invalid and describes it', () => {
    render(<Input label="Username" error="Required" />);
    const input = screen.getByLabelText('Username');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('alert')).toHaveTextContent('Required');
    expect(input.getAttribute('aria-describedby')).toBe(screen.getByRole('alert').id);
  });

  it('labels a Select and a Textarea the same way', () => {
    render(
      <>
        <Select label="Role">
          <option value="admin">Admin</option>
        </Select>
        <Textarea label="Notes" />
      </>
    );
    expect(screen.getByLabelText('Role')).toBeInTheDocument();
    expect(screen.getByLabelText('Notes')).toBeInTheDocument();
  });
});

describe('Badge / StatusPill', () => {
  it('renders badge content', () => {
    render(<Badge status="success">ENABLED</Badge>);
    expect(screen.getByText('ENABLED')).toBeInTheDocument();
  });

  it('renders a status pill with a hidden dot', () => {
    render(<StatusPill status="danger">OFFLINE</StatusPill>);
    expect(screen.getByText('OFFLINE')).toBeInTheDocument();
  });
});

describe('Alert / ErrorState', () => {
  it('renders as an alert region', () => {
    render(<Alert tone="danger">Something broke</Alert>);
    expect(screen.getByRole('alert')).toHaveTextContent('Something broke');
  });

  it('ErrorState renders a retry button that calls onRetry', async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Could not load" onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'RETRY' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('auto-dismisses after the given delay', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onDismiss = vi.fn();
    render(
      <Alert tone="success" autoDismiss={1000} onDismiss={onDismiss}>
        Saved
      </Alert>
    );
    expect(onDismiss).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000);
    expect(onDismiss).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});

describe('Table', () => {
  it('renders a caption for screen readers and standard cells', () => {
    render(
      <Table caption="Backups">
        <TableHead>
          <TableRow>
            <TableHeaderCell>Name</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
            <TableCell>backup-1.tar.gz</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument();
    expect(screen.getByText('backup-1.tar.gz')).toBeInTheDocument();
  });
});

describe('Modal', () => {
  it('renders nothing when closed', () => {
    render(
      <Modal open={false} onClose={() => {}} title="Confirm">
        body
      </Modal>
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders a labeled dialog when open and closes on Escape', async () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="Confirm">
        body
      </Modal>
    );
    const dialog = screen.getByRole('dialog', { name: 'Confirm' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
