// Last reviewed: 2025-04-30 11:32:10 UTC (User: TeeksssOrta)
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useInView } from 'react-intersection-observer';

interface VirtualListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  itemHeight: number | ((item: T, index: number) => number);
  overscanCount?: number;
  className?: string;
  style?: React.CSSProperties;
  onEndReached?: () => void;
  endReachedThreshold?: number;
  keyExtractor?: (item: T, index: number) => string;
  scrollToIndex?: number;
  onScroll?: (event: React.UIEvent<HTMLDivElement>) => void;
}

function VirtualList<T>({
  items,
  renderItem,
  itemHeight,
  overscanCount = 3,
  className = '',
  style = {},
  onEndReached,
  endReachedThreshold = 250,
  keyExtractor,
  scrollToIndex,
  onScroll,
}: VirtualListProps<T>) {
  // Refs for container and list
  const containerRef = useRef<HTMLDivElement>(null);
  
  // State for scroll position and dimensions
  const [scrollTop, setScrollTop] = useState<number>(0);
  const [containerHeight, setContainerHeight] = useState<number>(0);
  
  // End reached sentinel
  const { ref: endRef, inView: endInView } = useInView({
    rootMargin: `0px 0px ${endReachedThreshold}px 0px`,
    threshold: 0,
  });
  
  // Calculate item positions and total height
  const getItemHeight = useCallback(
    (item: T, index: number) => {
      return typeof itemHeight === 'function' ? itemHeight(item, index) : itemHeight;
    },
    [itemHeight]
  );
  
  // Calculate total list height
  const totalHeight = items.reduce((height, item, index) => {
    return height + getItemHeight(item, index);
  }, 0);
  
  // Calculate positions and visible items
  const getVisibleItems = useCallback(() => {
    if (!containerHeight) return { visibleItems: [], startIndex: 0, endIndex: 0 };
    
    let currentOffset = 0;
    let startIndex = -1;
    let endIndex = -1;
    
    // Find start index
    for (let i = 0; i < items.length; i++) {
      const height = getItemHeight(items[i], i);
      
      if (currentOffset + height > scrollTop - overscanCount * height) {
        startIndex = i;
        break;
      }
      
      currentOffset += height;
    }
    
    // If no start index was found (all items are above viewport)
    if (startIndex === -1) {
      return { visibleItems: [], startIndex: 0, endIndex: 0 };
    }
    
    // Find end index
    currentOffset = 0;
    for (let i = 0; i < items.length; i++) {
      const height = getItemHeight(items[i], i);
      
      if (currentOffset > scrollTop + containerHeight + overscanCount * height) {
        endIndex = i - 1;
        break;
      }
      
      currentOffset += height;
    }
    
    // If no end index was found (all items fit in viewport)
    if (endIndex === -1) {
      endIndex = items.length - 1;
    }
    
    // Extract visible items
    const visibleItems = items.slice(startIndex, endIndex + 1).map((item, relIndex) => {
      const index = startIndex + relIndex;
      const height = getItemHeight(item, index);
      
      // Calculate item offset
      let offset = 0;
      for (let i = 0; i < startIndex; i++) {
        offset += getItemHeight(items[i], i);
      }
      
      for (let i = startIndex; i < index; i++) {
        offset += getItemHeight(items[i], i);
      }
      
      return {
        item,
        index,
        height,
        offset,
      };
    });
    
    return { visibleItems, startIndex, endIndex };
  }, [items, getItemHeight, containerHeight, scrollTop, overscanCount]);
  
  // Handle scroll
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const scrollTop = event.currentTarget.scrollTop;
    setScrollTop(scrollTop);
    
    if (onScroll) {
      onScroll(event);
    }
  }, [onScroll]);
  
  // Measure container size
  useEffect(() => {
    if (containerRef.current) {
      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          if (entry.target === containerRef.current) {
            setContainerHeight(entry.contentRect.height);
          }
        }
      });
      
      resizeObserver.observe(containerRef.current);
      
      // Initial measurement
      setContainerHeight(containerRef.current.clientHeight);
      
      return () => {
        resizeObserver.disconnect();
      };
    }
  }, []);
  
  // Handle end reached
  useEffect(() => {
    if (endInView && onEndReached) {
      onEndReached();
    }
  }, [endInView, onEndReached]);
  
  // Scroll to specific index
  useEffect(() => {
    if (scrollToIndex !== undefined && containerRef.current) {
      let offset = 0;
      
      for (let i = 0; i < scrollToIndex && i < items.length; i++) {
        offset += getItemHeight(items[i], i);
      }
      
      containerRef.current.scrollTop = offset;
      setScrollTop(offset);
    }
  }, [scrollToIndex, items, getItemHeight]);
  
  // Calculate visible items
  const { visibleItems } = getVisibleItems();
  
  // Key extractor
  const getKey = (item: T, index: number): string => {
    if (keyExtractor) {
      return keyExtractor(item, index);
    }
    return `item-${index}`;
  };
  
  return (
    <div
      ref={containerRef}
      className={`virtual-list-container ${className}`}
      style={{
        height: '100%',
        overflow: 'auto',
        position: 'relative',
        ...style,
      }}
      onScroll={handleScroll}
    >
      <div
        className="virtual-list-content"
        style={{
          height: `${totalHeight}px`,
          position: 'relative',
        }}
      >
        {visibleItems.map(({ item, index, offset, height }) => (
          <div
            key={getKey(item, index)}
            className="virtual-list-item"
            style={{
              position: 'absolute',
              top: `${offset}px`,
              width: '100%',
              height: `${height}px`,
            }}
          >
            {renderItem(item, index)}
          </div>
        ))}
      </div>
      
      {/* End sentinel for infinite loading */}
      <div ref={endRef} style={{ height: 1 }} />
    </div>
  );
}

export default React.memo(VirtualList) as typeof VirtualList;