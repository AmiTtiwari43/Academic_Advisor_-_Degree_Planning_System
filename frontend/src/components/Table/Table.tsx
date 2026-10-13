import React from 'react';
import styles from './Table.module.css';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  width?: string;
}

export interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string | number;
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (key: string) => void;
  stickyHeader?: boolean;
  emptyState?: React.ReactNode;
  caption?: string;
  className?: string;
}

export function Table<T>({
  columns,
  data,
  keyExtractor,
  sortColumn,
  sortDirection = 'asc',
  onSort,
  stickyHeader = false,
  emptyState,
  caption,
  className = '',
}: TableProps<T>) {
  return (
    <div className={`${styles.tableWrapper} ${stickyHeader ? styles.stickyWrapper : ''} ${className}`}>
      <table className={styles.table}>
        {caption && <caption className={styles.caption}>{caption}</caption>}
        <thead className={`${styles.thead} ${stickyHeader ? styles.stickyHead : ''}`}>
          <tr>
            {columns.map((col) => {
              const isSorted = sortColumn === col.key;
              const alignClass = styles[col.align || 'left'];

              return (
                <th
                  key={col.key}
                  style={col.width ? { width: col.width } : undefined}
                  className={`${styles.th} ${alignClass}`}
                  scope="col"
                >
                  {col.sortable && onSort ? (
                    <button
                      type="button"
                      className={styles.sortButton}
                      onClick={() => onSort(col.key)}
                      aria-label={`Sort by ${col.header}`}
                    >
                      <span>{col.header}</span>
                      <span className={styles.sortIcon} aria-hidden="true">
                        {isSorted ? (sortDirection === 'asc' ? '▲' : '▼') : '⇅'}
                      </span>
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className={styles.tbody}>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className={styles.emptyCell}>
                {emptyState || <div className={styles.defaultEmpty}>No records found</div>}
              </td>
            </tr>
          ) : (
            data.map((item, rowIndex) => (
              <tr
                key={keyExtractor(item)}
                className={`${styles.tr} ${rowIndex % 2 === 1 ? styles.altRow : ''}`}
              >
                {columns.map((col) => {
                  const alignClass = styles[col.align || 'left'];
                  return (
                    <td key={col.key} className={`${styles.td} ${alignClass}`}>
                      {col.render
                        ? col.render(item)
                        : (item as Record<string, unknown>)[col.key] as React.ReactNode}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
