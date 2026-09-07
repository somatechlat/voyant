import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import * as echarts from 'echarts';

export type ChartType = 'line' | 'bar' | 'pie' | 'scatter' | 'gauge' | 'area' | 'radar';

@customElement('voyant-chart')
export class VoyantChart extends LitElement {
    @property({ type: String }) type: ChartType = 'line';
    @property({ type: Object }) data: Record<string, unknown> = {};
    @property({ type: Object }) options: Record<string, unknown> = {};
    @property({ type: String }) height = '300px';

    private chart: echarts.ECharts | null = null;
    private container: HTMLElement | null = null;

    createRenderRoot() { return this; }

    firstUpdated() {
        this.container = this.renderRoot.querySelector('.chart-container') as HTMLElement;
        if (this.container) {
            this.chart = echarts.init(this.container, 'dark');
            this._updateChart();
            const ro = new ResizeObserver(() => this.chart?.resize());
            ro.observe(this.container);
        }
    }

    updated() { this._updateChart(); }

    disconnectedCallback() {
        this.chart?.dispose();
        super.disconnectedCallback();
    }

    private _getThemeColors() {
        return ['#FF4D00', '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#EF4444'];
    }

    private _updateChart() {
        if (!this.chart) return;
        const colors = this._getThemeColors();

        const base: Record<string, unknown> = {
            backgroundColor: 'transparent',
            color: colors,
            textStyle: { fontFamily: 'Inter, system-ui, sans-serif', color: '#9CA3AF' },
            grid: { left: 48, right: 24, top: 40, bottom: 40, containLabel: true },
            tooltip: {
                trigger: this.type === 'pie' ? 'item' : 'axis',
                backgroundColor: '#141414',
                borderColor: '#262626',
                textStyle: { color: '#FAFAFA', fontSize: 12 },
            },
            legend: {
                textStyle: { color: '#9CA3AF', fontSize: 11 },
                top: 4,
                right: 4,
            },
        };

        let typeConfig: Record<string, unknown> = {};
        if (this.type === 'line' || this.type === 'area') {
            typeConfig = {
                xAxis: { type: 'category', data: this.data.labels as string[], axisLine: { lineStyle: { color: '#262626' } }, axisLabel: { color: '#9CA3AF' } },
                yAxis: { type: 'value', splitLine: { lineStyle: { color: '#1A1A1A' } }, axisLabel: { color: '#9CA3AF' } },
                series: (this.data.datasets as Array<Record<string, unknown>> || []).map(ds => ({
                    type: 'line',
                    name: ds.name,
                    data: ds.values,
                    smooth: true,
                    areaStyle: this.type === 'area' ? { opacity: 0.15 } : undefined,
                    lineStyle: { width: 2 },
                    symbolSize: 4,
                })),
            };
        } else if (this.type === 'bar') {
            typeConfig = {
                xAxis: { type: 'category', data: this.data.labels as string[], axisLine: { lineStyle: { color: '#262626' } }, axisLabel: { color: '#9CA3AF' } },
                yAxis: { type: 'value', splitLine: { lineStyle: { color: '#1A1A1A' } }, axisLabel: { color: '#9CA3AF' } },
                series: (this.data.datasets as Array<Record<string, unknown>> || []).map(ds => ({
                    type: 'bar',
                    name: ds.name,
                    data: ds.values,
                    barMaxWidth: 32,
                    itemStyle: { borderRadius: [4, 4, 0, 0] },
                })),
            };
        } else if (this.type === 'pie') {
            typeConfig = {
                series: [{
                    type: 'pie',
                    radius: ['40%', '70%'],
                    data: (this.data.items as Array<{ name: string; value: number }> || []).map((item, i) => ({
                        ...item, itemStyle: { color: colors[i % colors.length] },
                    })),
                    label: { color: '#9CA3AF', fontSize: 11 },
                    emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
                }],
            };
        } else if (this.type === 'gauge') {
            typeConfig = {
                series: [{
                    type: 'gauge',
                    progress: { show: true, width: 12, itemStyle: { color: '#FF4D00' } },
                    axisLine: { lineStyle: { width: 12, color: [[1, '#1A1A1A']] } },
                    axisTick: { show: false },
                    splitLine: { show: false },
                    axisLabel: { show: false },
                    pointer: { show: false },
                    anchor: { show: false },
                    title: { fontSize: 12, color: '#9CA3AF', offsetCenter: [0, '70%'] },
                    detail: { fontSize: 28, fontWeight: 'bold', color: '#FAFAFA', offsetCenter: [0, '0%'] },
                    data: [{ value: (this.data.value as number) || 0, name: (this.data.name as string) || '' }],
                }],
            };
        } else if (this.type === 'scatter') {
            typeConfig = {
                xAxis: { type: 'value', splitLine: { lineStyle: { color: '#1A1A1A' } }, axisLabel: { color: '#9CA3AF' } },
                yAxis: { type: 'value', splitLine: { lineStyle: { color: '#1A1A1A' } }, axisLabel: { color: '#9CA3AF' } },
                series: (this.data.datasets as Array<Record<string, unknown>> || []).map(ds => ({
                    type: 'scatter',
                    name: ds.name,
                    data: ds.values,
                    symbolSize: 8,
                })),
            };
        }

        this.chart.setOption({ ...base, ...typeConfig, ...this.options }, true);
    }

    render() {
        return html`<div class="chart-container" style="width:100%;height:${this.height}"></div>`;
    }
}
