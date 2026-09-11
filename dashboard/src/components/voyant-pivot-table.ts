import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface ValueField {
    field: string;
    agg: 'sum' | 'avg' | 'count' | 'min' | 'max';
}

interface PivotCell {
    raw: number | null;
    formatted: string;
}

interface PivotRow {
    rowKey: string[];
    cells: Map<string, PivotCell>;
    totals: Map<string, PivotCell>;
}

/**
 * Pivot table component for the Voyant dashboard.
 * Implements FR-5.4.1.4 (Pivot tables) from VOYANT_MIMO_MERGE_SPEC.
 *
 * @example
 *   <voyant-pivot-table
 *     .data=${salesData}
 *     .rowFields=${['region']}
 *     .columnFields=${['product']}
 *     .valueFields=${[{ field: 'revenue', agg: 'sum' }]}>
 *   </voyant-pivot-table>
 */
@customElement('voyant-pivot-table')
export class VoyantPivotTable extends LitElement {
    /** Flat array of objects (the source data). */
    @property({ type: Array }) data: Array<Record<string, unknown>> = [];
    /** Fields to group by on rows. */
    @property({ type: Array }) rowFields: string[] = [];
    /** Fields to group by on columns. */
    @property({ type: Array }) columnFields: string[] = [];
    /** Value fields with aggregation methods. */
    @property({ type: Array }) valueFields: ValueField[] = [];

    @state() private _sortColKey = '';
    @state() private _sortDir: 'asc' | 'desc' = 'asc';
    @state() private _sortRowIndex = -1; // -1 = no row-header sort

    createRenderRoot() { return this; }

    /* ─── Aggregation ─── */

    private _aggregate(values: number[], agg: string): number | null {
        if (values.length === 0) return null;
        switch (agg) {
            case 'sum': return values.reduce((a, b) => a + b, 0);
            case 'avg': return values.reduce((a, b) => a + b, 0) / values.length;
            case 'count': return values.length;
            case 'min': return Math.min(...values);
            case 'max': return Math.max(...values);
            default: return null;
        }
    }

    private _fmtNum(n: number | null): string {
        if (n === null || n === undefined) return '—';
        if (Number.isInteger(n)) return n.toLocaleString();
        return n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    /* ─── Pivot computation ─── */

    private _computePivot(): { colKeys: string[][]; rows: PivotRow[]; grandTotals: Map<string, PivotCell> } {
        const data = this.data;
        const rf = this.rowFields;
        const cf = this.columnFields;
        const vf = this.valueFields;

        if (!data.length || (!rf.length && !cf.length && !vf.length)) {
            return { colKeys: [], rows: [], grandTotals: new Map() };
        }

        // Build unique column keys (sorted)
        const colKeySet = new Map<string, string[]>();
        for (const row of data) {
            const ck = cf.map(f => String(row[f] ?? ''));
            const key = ck.join('\x00');
            if (!colKeySet.has(key)) colKeySet.set(key, ck);
        }
        const colKeys = Array.from(colKeySet.values()).sort((a, b) => a.join('').localeCompare(b.join('')));

        // Build row groups
        const rowGroupMap = new Map<string, { rowKey: string[]; items: Array<Record<string, unknown>> }>();
        for (const row of data) {
            const rk = rf.map(f => String(row[f] ?? ''));
            const key = rk.join('\x00');
            if (!rowGroupMap.has(key)) rowGroupMap.set(key, { rowKey: rk, items: [] });
            rowGroupMap.get(key)!.items.push(row);
        }

        const makeCell = (items: Array<Record<string, unknown>>, vfItem: ValueField): PivotCell => {
            const nums = items
                .map(r => r[vfItem.field])
                .filter(v => v != null && !isNaN(Number(v)))
                .map(Number);
            const raw = this._aggregate(nums, vfItem.agg);
            return { raw, formatted: this._fmtNum(raw) };
        };

        const makeCellKey = (vfItem: ValueField) => `${vfItem.field}|${vfItem.agg}`;

        // Build pivot rows
        const rows: PivotRow[] = [];
        for (const [, grp] of rowGroupMap) {
            const cells = new Map<string, PivotCell>();
            const totals = new Map<string, PivotCell>();
            for (const ck of colKeys) {
                const ckStr = ck.join('\x00');
                const matching = grp.items.filter(row => {
                    const rowCk = cf.map(f => String(row[f] ?? '')).join('\x00');
                    return rowCk === ckStr;
                });
                for (const vfItem of vf) {
                    const cellKey = ckStr + '\x01' + makeCellKey(vfItem);
                    cells.set(cellKey, makeCell(matching, vfItem));
                }
            }
            // Row totals
            for (const vfItem of vf) {
                totals.set(makeCellKey(vfItem), makeCell(grp.items, vfItem));
            }
            rows.push({ rowKey: grp.rowKey, cells, totals });
        }

        // Grand totals (column totals)
        const grandTotals = new Map<string, PivotCell>();
        for (const ck of colKeys) {
            const ckStr = ck.join('\x00');
            const matching = data.filter(row => {
                const rowCk = cf.map(f => String(row[f] ?? '')).join('\x00');
                return rowCk === ckStr;
            });
            for (const vfItem of vf) {
                grandTotals.set(ckStr + '\x01' + makeCellKey(vfItem), makeCell(matching, vfItem));
            }
        }
        // Overall grand total
        for (const vfItem of vf) {
            grandTotals.set('__grand__' + makeCellKey(vfItem), makeCell(data, vfItem));
        }

        return { colKeys, rows, grandTotals };
    }

    /* ─── Sorting ─── */

    private _sortedRows(rows: PivotRow[], colKeys: string[][]): PivotRow[] {
        if (this._sortRowIndex >= 0) {
            // Sort by row header field
            const idx = this._sortRowIndex;
            return [...rows].sort((a, b) => {
                const cmp = String(a.rowKey[idx] ?? '').localeCompare(String(b.rowKey[idx] ?? ''), undefined, { numeric: true });
                return this._sortDir === 'asc' ? cmp : -cmp;
            });
        }
        if (!this._sortColKey) return rows;
        const dir = this._sortDir === 'asc' ? 1 : -1;
        return [...rows].sort((a, b) => {
            const va = a.cells.get(this._sortColKey)?.raw ?? -Infinity;
            const vb = b.cells.get(this._sortColKey)?.raw ?? -Infinity;
            return (va - vb) * dir;
        });
    }

    private _toggleSortCell(colKey: string) {
        if (this._sortColKey === colKey) {
            this._sortDir = this._sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            this._sortColKey = colKey;
            this._sortDir = 'asc';
        }
        this._sortRowIndex = -1;
    }

    private _toggleSortRow(idx: number) {
        if (this._sortRowIndex === idx) {
            this._sortDir = this._sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            this._sortRowIndex = idx;
            this._sortDir = 'asc';
        }
        this._sortColKey = '';
    }

    /* ─── Export ─── */

    private _exportCSV(colKeys: string[][], rows: PivotRow[]) {
        const vf = this.valueFields;
        const makeCellKey = (vfItem: ValueField) => `${vfItem.field}|${vfItem.agg}`;

        // Header row
        const headerParts = [...this.rowFields];
        for (const ck of colKeys) {
            for (const vfItem of vf) {
                headerParts.push(ck.join(' / ') + ` (${vfItem.agg}(${vfItem.field}))`);
            }
        }
        // Totals column
        for (const vfItem of vf) {
            headerParts.push(`Total (${vfItem.agg}(${vfItem.field}))`);
        }

        const csvLines = [headerParts.map(h => h.includes(',') ? `"${h}"` : h).join(',')];

        for (const row of rows) {
            const parts: string[] = [...row.rowKey];
            for (const ck of colKeys) {
                const ckStr = ck.join('\x00');
                for (const vfItem of vf) {
                    const cellKey = ckStr + '\x01' + makeCellKey(vfItem);
                    const val = row.cells.get(cellKey);
                    parts.push(val?.raw != null ? String(val.raw) : '');
                }
            }
            for (const vfItem of vf) {
                const total = row.totals.get(makeCellKey(vfItem));
                parts.push(total?.raw != null ? String(total.raw) : '');
            }
            csvLines.push(parts.map(p => p.includes(',') ? `"${p}"` : p).join(','));
        }

        const blob = new Blob([csvLines.join('\n')], { type: 'text/csv' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'pivot-export.csv';
        a.click();
        URL.revokeObjectURL(a.href);
    }

    /* ─── Render ─── */

    render() {
        const { colKeys, rows, grandTotals } = this._computePivot();
        const vf = this.valueFields;
        const rf = this.rowFields;
        const cf = this.columnFields;
        const makeCellKey = (vfItem: ValueField) => `${vfItem.field}|${vfItem.agg}`;

        const sortedRows = this._sortedRows(rows, colKeys);
        const hasRows = rf.length > 0;
        const hasCols = cf.length > 0;
        const vfCount = Math.max(vf.length, 1);

        // Number of column header levels
        const colLevels = cf.length || 1;

        const cellStyle = 'padding:6px 12px;border:1px solid #1A1A1A;font-size:12px;white-space:nowrap';
        const headerStyle = 'padding:6px 12px;border:1px solid #262626;font-size:11px;font-weight:600;color:#9CA3AF;background:#0D0D0D;cursor:pointer;user-select:none;white-space:nowrap';
        const rowHeaderStyle = 'padding:6px 12px;border:1px solid #1A1A1A;font-size:12px;color:#D1D5DB;font-weight:500;cursor:pointer;user-select:none;white-space:nowrap;background:#0F0F0F';
        const totalCellStyle = 'padding:6px 12px;border:1px solid #262626;font-size:12px;font-weight:700;color:#FAFAFA;background:#111;white-space:nowrap';

        if (!this.data.length && !rows.length) {
            return html`<div style="text-align:center;padding:48px;color:#6B7280;font-family:Inter,system-ui,sans-serif;font-size:13px">No data to pivot</div>`;
        }

        return html`
            <div style="font-family:Inter,system-ui,sans-serif">
                <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center">
                    <span style="font-size:12px;color:#6B7280">Rows: ${rf.join(', ') || '—'} · Columns: ${cf.join(', ') || '—'} · Values: ${vf.map(v => `${v.agg}(${v.field})`).join(', ') || '—'}</span>
                    <span style="flex:1"></span>
                    <button @click=${() => this._exportCSV(colKeys, sortedRows)}
                        style="padding:6px 14px;border-radius:8px;border:1px solid #262626;background:#141414;color:#9CA3AF;font-size:11px;cursor:pointer">
                        📥 Export CSV
                    </button>
                </div>
                <div style="overflow-x:auto;border-radius:12px;border:1px solid #262626;background:#0A0A0A">
                    <table style="border-collapse:collapse;min-width:100%">
                        <thead>
                            ${hasCols ? this._renderColHeaders(colKeys, vf, headerStyle, rowHeaderStyle, makeCellKey, hasRows, rf.length || 1) : ''}
                            ${!hasCols && hasRows ? html`
                            <tr>
                                ${rf.map((f, i) => html`
                                    <th style="${rowHeaderStyle}" @click=${() => this._toggleSortRow(i)}>
                                        ${f} ${this._sortRowIndex === i ? (this._sortDir === 'asc' ? '↑' : '↓') : ''}
                                    </th>
                                `)}
                                ${vf.map(vfItem => html`
                                    <th style="${headerStyle}">${vfItem.agg}(${vfItem.field})</th>
                                `)}
                            </tr>` : ''}
                        </thead>
                        <tbody>
                            ${sortedRows.map(row => html`
                            <tr style="transition:background 0.1s"
                                @mouseenter=${(e: Event) => ((e.target as HTMLElement).closest('tr')!.style.background = '#141414')}
                                @mouseleave=${(e: Event) => ((e.target as HTMLElement).closest('tr')!.style.background = 'transparent')}>
                                ${hasRows ? row.rowKey.map((v, i) => html`
                                    <td style="${rowHeaderStyle}" @click=${() => this._toggleSortRow(i)}>${v || '—'}</td>
                                `) : ''}
                                ${colKeys.map(ck => {
                                    const ckStr = ck.join('\x00');
                                    return vf.map(vfItem => {
                                        const cellKey = ckStr + '\x01' + makeCellKey(vfItem);
                                        const cell = row.cells.get(cellKey);
                                        return html`<td style="${cellStyle};text-align:right;color:#D1D5DB">${cell?.formatted ?? '—'}</td>`;
                                    });
                                })}
                                ${vf.map(vfItem => {
                                    const total = row.totals.get(makeCellKey(vfItem));
                                    return html`<td style="${totalCellStyle};text-align:right">${total?.formatted ?? '—'}</td>`;
                                })}
                            </tr>`)}
                            ${sortedRows.length === 0 ? html`
                            <tr><td colspan=${(hasRows ? rf.length : 0) + colKeys.length * vfCount + vfCount}
                                style="text-align:center;padding:32px;color:#6B7280;font-size:12px">No data</td></tr>
                            ` : ''}
                        </tbody>
                        <tfoot>
                            <tr style="border-top:2px solid #262626;background:#111">
                                ${hasRows ? html`
                                    <td style="${totalCellStyle};font-size:11px;text-transform:uppercase;letter-spacing:0.05em" colspan=${rf.length}>Grand Total</td>
                                ` : ''}
                                ${colKeys.map(ck => {
                                    const ckStr = ck.join('\x00');
                                    return vf.map(vfItem => {
                                        const gt = grandTotals.get(ckStr + '\x01' + makeCellKey(vfItem));
                                        return html`<td style="${totalCellStyle};text-align:right">${gt?.formatted ?? '—'}</td>`;
                                    });
                                })}
                                ${vf.map(vfItem => {
                                    const gt = grandTotals.get('__grand__' + makeCellKey(vfItem));
                                    return html`<td style="${totalCellStyle};text-align:right;border:2px solid #333">${gt?.formatted ?? '—'}</td>`;
                                })}
                            </tr>
                        </tfoot>
                    </table>
                </div>
                <div style="font-size:11px;color:#4B5563;margin-top:8px">${sortedRows.length} rows × ${colKeys.length} columns</div>
            </div>
        `;
    }

    private _renderColHeaders(
        colKeys: string[][],
        vf: ValueField[],
        headerStyle: string,
        rowHeaderStyle: string,
        makeCellKey: (v: ValueField) => string,
        hasRows: boolean,
        rowSpan: number,
    ) {
        const vfCount = Math.max(vf.length, 1);

        // For single column field, simple headers
        if (this.columnFields.length === 1) {
            return html`
                ${hasRows ? html`<tr>
                    <th style="${rowHeaderStyle}" rowspan="2" @click=${() => this._toggleSortRow(0)}>
                        ${this.rowFields[0] || ''} ${this._sortRowIndex === 0 ? (this._sortDir === 'asc' ? '↑' : '↓') : ''}
                    </th>
                    ${colKeys.map(ck => html`
                        <th style="${headerStyle};text-align:center" colspan=${vfCount}>
                            ${ck[0] || '—'}
                        </th>
                    `)}
                    <th style="${headerStyle};text-align:center" colspan=${vfCount}>Total</th>
                </tr>` : ''}
                <tr>
                    ${!hasRows ? html`<th style="${rowHeaderStyle}">${this.rowFields[0] || ''}</th>` : ''}
                    ${colKeys.map(ck => {
                        const ckStr = ck.join('\x00');
                        return vf.map(vfItem => {
                            const cellKey = ckStr + '\x01' + makeCellKey(vfItem);
                            const isActive = this._sortColKey === cellKey;
                            return html`<th style="${headerStyle};text-align:right;font-size:10px;font-weight:500;${isActive ? 'color:#FF4D00' : ''}"
                                @click=${() => this._toggleSortCell(cellKey)}>
                                ${vfItem.agg}(${vfItem.field})${isActive ? (this._sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                            </th>`;
                        });
                    })}
                    ${vf.map(vfItem => html`
                        <th style="${headerStyle};text-align:right;font-size:10px;font-weight:500">${vfItem.agg}(${vfItem.field})</th>
                    `)}
                </tr>
            `;
        }

        // Multi-level column headers
        return html`
            ${hasRows ? html`<tr>
                <th style="${rowHeaderStyle}" rowspan=${this.columnFields.length + (vfCount > 1 ? 1 : 0)}>
                    ${this.rowFields.join(' / ')}
                </th>
                ${colKeys.map(ck => ck.map((level, _i) => html`
                    <th style="${headerStyle}" colspan=${vfCount}>${level || '—'}</th>
                `))}
                <th style="${headerStyle}" colspan=${vfCount}>Total</th>
            </tr>` : ''}
            ${vfCount > 1 ? html`<tr>
                ${colKeys.map(ck => {
                    const ckStr = ck.join('\x00');
                    return vf.map(vfItem => {
                        const cellKey = ckStr + '\x01' + makeCellKey(vfItem);
                        const isActive = this._sortColKey === cellKey;
                        return html`<th style="${headerStyle};text-align:right;font-size:10px;${isActive ? 'color:#FF4D00' : ''}"
                            @click=${() => this._toggleSortCell(cellKey)}>
                            ${vfItem.agg}(${vfItem.field})${isActive ? (this._sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                        </th>`;
                    });
                })}
                ${vf.map(vfItem => html`
                    <th style="${headerStyle};text-align:right;font-size:10px">${vfItem.agg}(${vfItem.field})</th>
                `)}
            </tr>` : ''}
        `;
    }
}
