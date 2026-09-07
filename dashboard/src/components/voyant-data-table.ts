import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface TableColumn {
    key: string;
    label: string;
    width?: string;
    sortable?: boolean;
    format?: 'text' | 'number' | 'date' | 'boolean' | 'badge' | 'json';
    badgeColors?: Record<string, string>;
}

@customElement('voyant-data-table')
export class VoyantDataTable extends LitElement {
    @property({ type: Array }) columns: TableColumn[] = [];
    @property({ type: Array }) rows: Array<Record<string, unknown>> = [];
    @property({ type: String }) height = 'auto';
    @property({ type: Boolean }) exportable = true;
    @property({ type: Boolean }) filterable = true;

    @state() sortKey = '';
    @state() sortDir: 'asc' | 'desc' = 'asc';
    @state() filterText = '';
    @state() page = 0;
    @state() pageSize = 50;

    createRenderRoot() { return this; }

    private _sorted() {
        let data = [...this.rows];
        if (this.filterText) {
            const q = this.filterText.toLowerCase();
            data = data.filter(row => Object.values(row).some(v => String(v).toLowerCase().includes(q)));
        }
        if (this.sortKey) {
            data.sort((a, b) => {
                const va = a[this.sortKey] ?? '';
                const vb = b[this.sortKey] ?? '';
                const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true });
                return this.sortDir === 'asc' ? cmp : -cmp;
            });
        }
        return data;
    }

    private _paginated(data: Array<Record<string, unknown>>) {
        return data.slice(this.page * this.pageSize, (this.page + 1) * this.pageSize);
    }

    private _toggleSort(key: string) {
        if (this.sortKey === key) {
            this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortKey = key;
            this.sortDir = 'asc';
        }
    }

    private _exportCSV() {
        const headers = this.columns.map(c => c.label).join(',');
        const rows = this._sorted().map(row => this.columns.map(c => {
            const v = row[c.key] ?? '';
            return typeof v === 'string' && v.includes(',') ? `"${v}"` : String(v);
        }).join(',')).join('\n');
        const csv = `${headers}\n${rows}`;
        const blob = new Blob([csv], { type: 'text/csv' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'export.csv';
        a.click();
    }

    private _formatCell(value: unknown, col: TableColumn): string {
        if (value == null) return '—';
        if (col.format === 'number') return typeof value === 'number' ? value.toLocaleString() : String(value);
        if (col.format === 'date') return new Date(String(value)).toLocaleString();
        if (col.format === 'boolean') return value ? '✓' : '✗';
        if (col.format === 'json') return typeof value === 'object' ? JSON.stringify(value).slice(0, 80) : String(value);
        return String(value);
    }

    render() {
        const filtered = this._sorted();
        const paged = this._paginated(filtered);
        const totalPages = Math.ceil(filtered.length / this.pageSize);

        return html`
            <div style="font-family:Inter,system-ui,sans-serif">
                ${this.filterable || this.exportable ? html`
                <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center">
                    ${this.filterable ? html`
                    <input type="text" placeholder="Filter..." .value=${this.filterText}
                        @input=${(e: Event) => { this.filterText = (e.target as HTMLInputElement).value; this.page = 0; }}
                        style="flex:1;padding:8px 12px;border-radius:8px;border:1px solid #262626;background:#141414;color:#FAFAFA;font-size:13px;outline:none" />
                    ` : ''}
                    ${this.exportable ? html`
                    <button @click=${this._exportCSV}
                        style="padding:8px 16px;border-radius:8px;border:1px solid #262626;background:#141414;color:#9CA3AF;font-size:12px;cursor:pointer">
                        📥 CSV
                    </button>
                    ` : ''}
                    <span style="font-size:11px;color:#6B7280">${filtered.length} rows</span>
                </div>` : ''}
                <div style="overflow-x:auto;border-radius:12px;border:1px solid #262626;background:#0A0A0A">
                    <table style="width:100%;border-collapse:collapse;font-size:13px">
                        <thead>
                            <tr style="border-bottom:1px solid #262626">
                                ${this.columns.map(col => html`
                                <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:0.05em;cursor:${col.sortable !== false ? 'pointer' : 'default'};width:${col.width || 'auto'};white-space:nowrap"
                                    @click=${col.sortable !== false ? () => this._toggleSort(col.key) : null}">
                                    ${col.label}${this.sortKey === col.key ? (this.sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                                </th>`)}
                            </tr>
                        </thead>
                        <tbody>
                            ${paged.map(row => html`
                            <tr style="border-bottom:1px solid #1A1A1A;transition:background 0.1s"
                                @mouseenter=${(e: Event) => ((e.target as HTMLElement).closest('tr')!.style.background = '#141414')}
                                @mouseleave=${(e: Event) => ((e.target as HTMLElement).closest('tr')!.style.background = 'transparent')}>
                                ${this.columns.map(col => html`
                                <td style="padding:8px 16px;color:#D1D5DB;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:300px;font-family:${col.format === 'json' ? '"JetBrains Mono",monospace' : 'inherit'}">
                                    ${col.format === 'badge' && col.badgeColors ? html`
                                        <span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:${col.badgeColors[String(row[col.key])] || '#262626'};color:#FAFAFA">
                                            ${this._formatCell(row[col.key], col)}
                                        </span>
                                    ` : this._formatCell(row[col.key], col)}
                                </td>`)}
                            </tr>`)}
                            ${paged.length === 0 ? html`
                            <tr><td colspan=${this.columns.length} style="text-align:center;padding:48px;color:#6B7280">No data</td></tr>
                            ` : ''}
                        </tbody>
                    </table>
                </div>
                ${totalPages > 1 ? html`
                <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;font-size:12px;color:#6B7280">
                    <span>Page ${this.page + 1} of ${totalPages}</span>
                    <div style="display:flex;gap:4px">
                        <button ?disabled=${this.page === 0} @click=${() => this.page--}
                            style="padding:4px 12px;border-radius:6px;border:1px solid #262626;background:#141414;color:#9CA3AF;cursor:pointer;font-size:12px">←</button>
                        <button ?disabled=${this.page >= totalPages - 1} @click=${() => this.page++}
                            style="padding:4px 12px;border-radius:6px;border:1px solid #262626;background:#141414;color:#9CA3AF;cursor:pointer;font-size:12px">→</button>
                    </div>
                </div>` : ''}
            </div>
        `;
    }
}
