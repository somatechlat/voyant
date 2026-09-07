import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import * as monaco from 'monaco-editor';

@customElement('voyant-monaco-editor')
export class VoyantMonacoEditor extends LitElement {
    @property({ type: String }) value = '';
    @property({ type: String }) language = 'sql';
    @property({ type: String }) height = '300px';
    @property({ type: Boolean }) readOnly = false;
    @property({ type: String }) placeholder = '';

    @state() private _editor: monaco.editor.IStandaloneCodeEditor | null = null;
    private _container: HTMLElement | null = null;

    createRenderRoot() { return this; }

    firstUpdated() {
        this._container = this.renderRoot.querySelector('.editor-container') as HTMLElement;
        if (!this._container) return;

        monaco.editor.defineTheme('voyant-dark', {
            base: 'vs-dark',
            inherit: true,
            rules: [
                { token: 'keyword', foreground: 'FF4D00', fontStyle: 'bold' },
                { token: 'string', foreground: '10B981' },
                { token: 'number', foreground: 'F59E0B' },
                { token: 'comment', foreground: '6B7280', fontStyle: 'italic' },
                { token: 'operator', foreground: '3B82F6' },
                { token: 'type', foreground: '8B5CF6' },
                { token: 'function', foreground: '06B6D4' },
            ],
            colors: {
                'editor.background': '#0A0A0A',
                'editor.foreground': '#FAFAFA',
                'editor.lineHighlightBackground': '#141414',
                'editor.selectionBackground': '#FF4D0033',
                'editorCursor.foreground': '#FF4D00',
                'editorLineNumber.foreground': '#3A3A3A',
                'editorLineNumber.activeForeground': '#9CA3AF',
                'editor.inactiveSelectionBackground': '#FF4D001A',
                'editorWidget.background': '#141414',
                'editorWidget.border': '#262626',
                'editorSuggestWidget.background': '#141414',
                'editorSuggestWidget.border': '#262626',
                'editorSuggestWidget.selectedBackground': '#1A1A1A',
                'minimap.background': '#0A0A0A',
            },
        });

        this._editor = monaco.editor.create(this._container, {
            value: this.value,
            language: this.language,
            theme: 'voyant-dark',
            readOnly: this.readOnly,
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: '"JetBrains Mono", "SF Mono", "Fira Code", monospace',
            fontLigatures: true,
            lineHeight: 22,
            padding: { top: 16, bottom: 16 },
            scrollBeyondLastLine: false,
            smoothScrolling: true,
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
            renderLineHighlight: 'gutter',
            roundedSelection: true,
            bracketPairColorization: { enabled: true },
            automaticLayout: true,
            tabSize: 2,
            wordWrap: 'on',
            suggestOnTriggerCharacters: true,
            quickSuggestions: true,
            placeholder: this.placeholder,
        });

        this._editor.onDidChangeModelContent(() => {
            this.value = this._editor!.getValue();
            this.dispatchEvent(new CustomEvent('change', { detail: { value: this.value } }));
        });

        // Add Ctrl+Enter to run
        this._editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
            this.dispatchEvent(new CustomEvent('run', { detail: { value: this.value } }));
        });

        const ro = new ResizeObserver(() => this._editor?.layout());
        ro.observe(this._container);
    }

    disconnectedCallback() {
        this._editor?.dispose();
        super.disconnectedCallback();
    }

    render() {
        return html`
            <div class="editor-container" style="width:100%;height:${this.height};border-radius:8px;overflow:hidden;border:1px solid #262626"></div>
        `;
    }
}
