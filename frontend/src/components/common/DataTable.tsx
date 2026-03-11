import React, { useState } from 'react'

interface Column<T> {
  key: string
  header: string
  render?: (item: T) => React.ReactNode
  sortable?: boolean
  width?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  total?: number
  page?: number
  perPage?: number
  onPageChange?: (page: number) => void
  onSort?: (key: string, order: 'asc' | 'desc') => void
  loading?: boolean
}

export default function DataTable<T extends Record<string, any>>({
  columns,
  data,
  total,
  page = 1,
  perPage = 20,
  onPageChange,
  onSort,
  loading,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const handleSort = (key: string) => {
    const newOrder = sortKey === key && sortOrder === 'desc' ? 'asc' : 'desc'
    setSortKey(key)
    setSortOrder(newOrder)
    onSort?.(key, newOrder)
  }

  const totalPages = total ? Math.ceil(total / perPage) : 1

  return (
    <div style={{
      background: 'var(--color-card)',
      borderRadius: 'var(--radius)',
      boxShadow: 'var(--shadow-card)',
      overflow: 'hidden',
    }}>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
              {columns.map(col => (
                <th
                  key={col.key}
                  onClick={() => col.sortable && handleSort(col.key)}
                  style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    fontWeight: 600,
                    color: 'var(--color-text-secondary)',
                    cursor: col.sortable ? 'pointer' : 'default',
                    width: col.width,
                    whiteSpace: 'nowrap',
                    userSelect: 'none',
                  }}
                >
                  {col.header}
                  {col.sortable && sortKey === col.key && (
                    <span style={{ marginLeft: '0.25rem' }}>
                      {sortOrder === 'asc' ? '\u25B2' : '\u25BC'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}
                >
                  Loading...
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}
                >
                  No data found
                </td>
              </tr>
            ) : (
              data.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                  {columns.map(col => (
                    <td key={col.key} style={{ padding: '0.75rem 1rem' }}>
                      {col.render ? col.render(item) : String(item[col.key] ?? '-')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {total != null && total > perPage && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.75rem 1rem',
          borderTop: '1px solid var(--color-border)',
          fontSize: '0.8rem',
          color: 'var(--color-text-secondary)',
        }}>
          <span>
            Showing {((page - 1) * perPage) + 1}&ndash;{Math.min(page * perPage, total)} of {total}
          </span>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              disabled={page <= 1}
              onClick={() => onPageChange?.(page - 1)}
              style={{
                padding: '0.375rem 0.75rem',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius)',
                background: 'var(--color-card)',
                cursor: page <= 1 ? 'not-allowed' : 'pointer',
                opacity: page <= 1 ? 0.5 : 1,
              }}
            >
              Previous
            </button>
            <span style={{ padding: '0.375rem 0.5rem' }}>
              Page {page} of {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => onPageChange?.(page + 1)}
              style={{
                padding: '0.375rem 0.75rem',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius)',
                background: 'var(--color-card)',
                cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                opacity: page >= totalPages ? 0.5 : 1,
              }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
