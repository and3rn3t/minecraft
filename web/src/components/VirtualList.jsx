import { useEffect, useMemo, useRef, useState } from 'react';

/**
 * Virtual scrolling component for rendering large lists efficiently
 * Only renders visible items plus a buffer
 */
export function VirtualList({
  items,
  renderItem,
  itemHeight = 50,
  overscan = 5,
  containerHeight = 400,
  className = '',
}) {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef(null);

  const { startIndex, endIndex, totalHeight, offsetY } = useMemo(() => {
    const containerHeightNum = typeof containerHeight === 'number' ? containerHeight : 400;
    const itemHeightNum = typeof itemHeight === 'number' ? itemHeight : 50;

    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeightNum) - overscan);
    const visibleCount = Math.ceil(containerHeightNum / itemHeightNum);
    const endIndex = Math.min(items.length, startIndex + visibleCount + overscan * 2);

    const totalHeight = items.length * itemHeightNum;
    const offsetY = startIndex * itemHeightNum;

    return { startIndex, endIndex, totalHeight, offsetY };
  }, [scrollTop, items.length, itemHeight, overscan, containerHeight]);

  const visibleItems = useMemo(() => {
    return items.slice(startIndex, endIndex).map((item, index) => ({
      item,
      index: startIndex + index,
    }));
  }, [items, startIndex, endIndex]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = e => {
      setScrollTop(e.target.scrollTop);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        height: typeof containerHeight === 'number' ? `${containerHeight}px` : containerHeight,
        overflow: 'auto',
      }}
    >
      <div style={{ height: `${totalHeight}px`, position: 'relative' }}>
        <div
          style={{
            transform: `translateY(${offsetY}px)`,
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
          }}
        >
          {visibleItems.map(({ item, index }) => (
            <div
              key={index}
              style={{
                height: typeof itemHeight === 'number' ? `${itemHeight}px` : itemHeight,
              }}
            >
              {renderItem(item, index)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default VirtualList;
