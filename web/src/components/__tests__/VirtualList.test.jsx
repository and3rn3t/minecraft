import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import VirtualList from '../VirtualList';

const items = Array.from({ length: 1000 }, (_, i) => `line ${i}`);
const renderList = props =>
  render(
    <VirtualList
      items={items}
      itemHeight={20}
      containerHeight={100}
      overscan={2}
      renderItem={item => <span>{item}</span>}
      {...props}
    />
  );

describe('VirtualList', () => {
  it('renders only what fits, plus the overscan', () => {
    renderList();

    // 100px / 20px = 5 visible, plus 2 * 2 overscan
    expect(screen.getAllByText(/^line /)).toHaveLength(9);
    expect(screen.getByText('line 0')).toBeInTheDocument();
    expect(screen.queryByText('line 9')).not.toBeInTheDocument();
  });

  it('sizes the scroll area for every item', () => {
    const { container } = renderList();
    expect(container.firstChild.firstChild).toHaveStyle({ height: '20000px' });
  });

  it('renders the rows that scroll into view', () => {
    const { container } = renderList();

    fireEvent.scroll(container.firstChild, { target: { scrollTop: 10000 } });

    // Row 500 is at the top: rows 498..506 are rendered
    expect(screen.getByText('line 500')).toBeInTheDocument();
    expect(screen.getByText('line 498')).toBeInTheDocument();
    expect(screen.queryByText('line 0')).not.toBeInTheDocument();
    expect(screen.queryByText('line 510')).not.toBeInTheDocument();
  });

  it('copes with fewer items than fit', () => {
    render(<VirtualList items={['only']} renderItem={item => <span>{item}</span>} />);
    expect(screen.getAllByText('only')).toHaveLength(1);
  });
});
