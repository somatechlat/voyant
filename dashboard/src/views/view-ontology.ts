import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-graph-view';
import '../components/voyant-data-table';
import '../components/voyant-detail-panel';
import '../components/voyant-metric-card';
import '../components/voyant-monaco-editor';

/* ── Interfaces ─────────────────────────────────────────────────────────── */

interface ObjectType {
    id: string;
    name: string;
    description: string;
    version: number;
    property_count: number;
    instance_count: number;
    tenant_id: string;
    created_at: string;
    properties?: PropertyDef[];
}

interface PropertyDef {
    id: string;
    name: string;
    property_type: string;
    required: boolean;
    default_value?: unknown;
    validation_rules?: unknown;
}

interface LinkType {
    id: string;
    name: string;
    source_type: string;
    target_type: string;
    cardinality: string;
    instance_count?: number;
}

interface ObjectInstance {
    id: string;
    object_type: string;
    object_type_name?: string;
    properties: Record<string, unknown>;
    version: number;
    tenant_id: string;
    created_at: string;
}

interface LinkInstance {
    id: string;
    link_type: string;
    link_type_name: string;
    source_object: string;
    target_object: string;
    properties: Record<string, unknown>;
    tenant_id: string;
}

type TableSubTab = 'object-types' | 'object-instances' | 'link-types' | 'link-instances';
type MainView = 'table' | 'grid' | 'graph' | 'builders';
type DetailTarget =
    | { kind: 'type'; data: ObjectType }
    | { kind: 'instance'; data: ObjectInstance }
    | null;

/* ── Builder Interfaces ───────────────────────────────────────────────── */

interface FilterCondition {
    id: string;
    field: string;
    operator: '=' | '!=' | '>' | '<' | '>=' | '<=' | 'contains' | 'starts_with' | 'ends_with';
    value: string;
}

interface TypePropertyForm {
    name: string;
    property_type: string;
    required: boolean;
    default_value: string;
    validation_regex: string;
    validation_min: string;
    validation_max: string;
}

interface ActionParamForm {
    name: string;
    param_type: string;
    required: boolean;
    default_value: string;
}

interface ActionRuleForm {
    rule_type: string;
    field: string;
    expected_value: string;
}

interface SideEffectForm {
    effect_type: string;
    url: string;
    channel: string;
}

interface UndoRuleForm {
    rule_type: string;
    field: string;
}

interface ActionTypeDef {
    id: string;
    name: string;
    description: string;
    parameters: any[];
    rules: any[];
    side_effects: any[];
    undoable: boolean;
    status: string;
}

interface FunctionDef {
    id: string;
    name: string;
    language: string;
    source_code: string;
    entry_point: string;
    input_schema: any;
    output_schema: any;
    status: string;
}

const PROPERTY_TYPES = ['string', 'integer', 'float', 'boolean', 'date', 'timestamp', 'enum', 'array', 'map', 'struct', 'geopoint'] as const;
const FILTER_OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'contains', 'starts_with', 'ends_with'] as const;
const PARAM_TYPES = ['string', 'integer', 'float', 'boolean', 'array', 'object', 'enum', 'date', 'timestamp'] as const;
const RULE_TYPES = ['status_check', 'field_exists', 'field_value', 'permission_check'] as const;
const SIDE_EFFECT_TYPES = ['notification', 'webhook', 'audit_log', 'field_update'] as const;
const UNDO_RULE_TYPES = ['status_revert', 'field_revert'] as const;

const PYTHON_TEMPLATE = `def handler(input_data):
    """Process input and return result."""
    return {"status": "ok", "received": input_data}
`;

const TYPESCRIPT_TEMPLATE = `export function handler(inputData: Record<string, any>) {
    // Process input and return result
    return { status: "ok", received: inputData };
}
`;

/* ── Component ──────────────────────────────────────────────────────────── */

@customElement('view-ontology')
export class ViewOntology extends LitElement {
    @state() types: ObjectType[] = [];
    @state() links: LinkType[] = [];
    @state() objectInstances: ObjectInstance[] = [];
    @state() linkInstances: LinkInstance[] = [];
    @state() loading = true;
    @state() loadingInstances = false;
    @state() loadingLinkInstances = false;

    @state() view: MainView = 'table';
    @state() tableSubTab: TableSubTab = 'object-types';
    @state() searchQuery = '';

    @state() detailTarget: DetailTarget = null;
    @state() detailOpen = false;
    @state() detailProperties: PropertyDef[] = [];
    @state() detailPanelTab: 'overview' | 'actions' | 'functions' = 'overview';
    @state() typeActions: ActionTypeDef[] = [];
    @state() typeFunctions: FunctionDef[] = [];
    @state() loadingActions = false;
    @state() loadingFunctions = false;

    @state() selectedInstanceTypeId: string | null = null;

    /* ── Filter Builder State ─────────────────────────────────────────── */
    @state() filterConditions: FilterCondition[] = [];
    @state() filterLogic: 'AND' | 'OR' = 'AND';
    @state() filterTargetType: string = '';
    @state() filterResults: ObjectInstance[] = [];
    @state() filterLoading = false;
    @state() filterBuilderOpen = false;

    /* ── Type Builder State ───────────────────────────────────────────── */
    @state() typeBuilderOpen = false;
    @state() typeName = '';
    @state() typeDescription = '';
    @state() typeProperties: TypePropertyForm[] = [];
    @state() typeSubmitting = false;
    @state() typeShowPreview = false;

    /* ── Action Builder State ─────────────────────────────────────────── */
    @state() actionBuilderOpen = false;
    @state() actionName = '';
    @state() actionDescription = '';
    @state() actionTargetType: string = '';
    @state() actionParams: ActionParamForm[] = [];
    @state() actionRules: ActionRuleForm[] = [];
    @state() actionSideEffects: SideEffectForm[] = [];
    @state() actionUndoable = false;
    @state() actionUndoRules: UndoRuleForm[] = [];
    @state() actionSubmitting = false;

    /* ── Function Editor State ────────────────────────────────────────── */
    @state() functionEditorOpen = false;
    @state() funcEditorOpen = false;
    @state() funcEditorEditing: FunctionDef | null = null;
    @state() functionName = '';
    @state() functionDescription = '';
    @state() functionLanguage: 'python' | 'typescript' = 'python';
    @state() functionSourceCode = '';
    @state() functionInputSchema = '{}';
    @state() functionOutputSchema = '{}';
    @state() functionRunning = false;
    @state() functionOutput = '';
    @state() functionError = '';
    @state() functionSubmitting = false;

    /* ── Edit Instance Modal State ────────────────────────────────────── */
    @state() editInstanceOpen = false;
    @state() editInstanceData: ObjectInstance | null = null;
    @state() editInstanceProps: Record<string, string> = {};
    @state() editInstanceSubmitting = false;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this._loadData();
    }

    /* ── Data Loading ──────────────────────────────────────────────────── */

    async _loadData() {
        this.loading = true;
        try {
            const [typesRes, linkTypesRes] = await Promise.all([
                api.get<ObjectType[]>('/admin/ontology/types').catch(() => [] as ObjectType[]),
                api.get<LinkType[]>('/admin/ontology/links').catch(() => [] as LinkType[]),
            ]);
            this.types = typesRes || [];
            this.links = linkTypesRes || [];
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    async _loadObjectInstances(typeId?: string) {
        this.loadingInstances = true;
        try {
            const params = typeId ? `?object_type_id=${typeId}` : '';
            this.objectInstances = await api.get<ObjectInstance[]>(`/ontology/objects${params}&limit=500`).catch(() => []);
        } catch { this.objectInstances = []; }
        finally { this.loadingInstances = false; }
    }

    async _loadLinkInstances() {
        this.loadingLinkInstances = true;
        try {
            this.linkInstances = await api.get<LinkInstance[]>('/ontology/links?limit=500').catch(() => []);
        } catch { this.linkInstances = []; }
        finally { this.loadingLinkInstances = false; }
    }

    async _loadTypeProperties(typeId: string) {
        try {
            this.detailProperties = await api.get<PropertyDef[]>(`/ontology/types/${typeId}`).then((r: any) => r.properties || []).catch(() => []);
        } catch { this.detailProperties = []; }
    }

    async _loadTypeActions(typeId: string) {
        this.loadingActions = true;
        try {
            this.typeActions = await api.get<ActionTypeDef[]>(`/ontology/actions?object_type_id=${typeId}`).catch(() => []);
        } catch { this.typeActions = []; }
        finally { this.loadingActions = false; }
    }

    async _loadTypeFunctions(typeId: string) {
        this.loadingFunctions = true;
        try {
            this.typeFunctions = await api.get<FunctionDef[]>(`/ontology/functions?object_type_id=${typeId}`).catch(() => []);
        } catch { this.typeFunctions = []; }
        finally { this.loadingFunctions = false; }
    }

    /* ── Tab switching ─────────────────────────────────────────────────── */

    private _switchTableTab(tab: TableSubTab) {
        this.tableSubTab = tab;
        this.searchQuery = '';
        if (tab === 'object-instances' && this.objectInstances.length === 0) {
            this._loadObjectInstances(this.selectedInstanceTypeId || undefined);
        }
        if (tab === 'link-instances' && this.linkInstances.length === 0) {
            this._loadLinkInstances();
        }
    }

    /* ── Search ────────────────────────────────────────────────────────── */

    private _filterSearch<T extends Record<string, unknown>>(rows: T[]): T[] {
        if (!this.searchQuery) return rows;
        const q = this.searchQuery.toLowerCase();
        return rows.filter(r => Object.values(r).some(v => String(v ?? '').toLowerCase().includes(q)));
    }

    /* ── Detail Panel Handlers ─────────────────────────────────────────── */

    private async _openTypeDetail(t: ObjectType) {
        this.detailTarget = { kind: 'type', data: t };
        this.detailOpen = true;
        this.detailPanelTab = 'overview';
        await this._loadTypeProperties(t.id);
        this._loadTypeActions(t.id);
        this._loadTypeFunctions(t.id);
    }

    private async _openInstanceDetail(inst: ObjectInstance) {
        this.detailTarget = { kind: 'instance', data: inst };
        this.detailOpen = true;
    }

    private _closeDetail() {
        this.detailOpen = false;
        this.detailTarget = null;
        this.detailProperties = [];
        this.detailPanelTab = 'overview';
        this.typeActions = [];
        this.typeFunctions = [];
    }

    private _editType(t: ObjectType) {
        this._closeDetail();
        this.typeName = t.name;
        this.typeDescription = t.description || '';
        this.typeProperties = (t.properties || this.detailProperties).map(p => ({
            name: p.name,
            property_type: p.property_type,
            required: p.required,
            default_value: p.default_value != null ? String(p.default_value) : '',
            validation_regex: (p.validation_rules as any)?.regex || '',
            validation_min: (p.validation_rules as any)?.min != null ? String((p.validation_rules as any).min) : '',
            validation_max: (p.validation_rules as any)?.max != null ? String((p.validation_rules as any).max) : '',
        }));
        this.typeShowPreview = false;
        this.typeBuilderOpen = true;
    }

    /* ── Delete handler ────────────────────────────────────────────────── */

    private async _deleteType(typeId: string, name: string) {
        if (!confirm(`Delete object type "${name}"? This cannot be undone.`)) return;
        try {
            await api.del(`/ontology/types/${typeId}`);
            this.types = this.types.filter(t => t.id !== typeId);
            this._closeDetail();
        } catch (err) {
            alert(`Failed to delete: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
    }

    private async _deleteInstance(instanceId: string) {
        if (!confirm('Delete this object instance?')) return;
        try {
            await api.del(`/ontology/objects/${instanceId}`);
            this.objectInstances = this.objectInstances.filter(i => i.id !== instanceId);
            this._closeDetail();
        } catch (err) {
            alert(`Failed to delete: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
    }

    /* ── Edit Instance Modal ────────────────────────────────────────────── */

    private _openEditInstance(inst: ObjectInstance) {
        this.editInstanceData = inst;
        this.editInstanceProps = {};
        for (const [k, v] of Object.entries(inst.properties || {})) {
            this.editInstanceProps[k] = typeof v === 'object' ? JSON.stringify(v) : String(v ?? '');
        }
        this.editInstanceOpen = true;
    }

    private _closeEditInstance() {
        this.editInstanceOpen = false;
        this.editInstanceData = null;
        this.editInstanceProps = {};
    }

    private _updateEditInstanceProp(key: string, value: string) {
        this.editInstanceProps = { ...this.editInstanceProps, [key]: value };
    }

    private async _submitEditInstance() {
        if (!this.editInstanceData) return;
        this.editInstanceSubmitting = true;
        try {
            const properties: Record<string, unknown> = {};
            for (const [k, v] of Object.entries(this.editInstanceProps)) {
                try { properties[k] = JSON.parse(v); } catch { properties[k] = v; }
            }
            await api.put(`/ontology/objects/${this.editInstanceData.id}`, { properties });
            // Refresh instances
            await this._loadObjectInstances(this.editInstanceData.object_type);
            // Update detail if open
            const updated = this.objectInstances.find(i => i.id === this.editInstanceData?.id);
            if (updated && this.detailTarget?.kind === 'instance') {
                this.detailTarget = { kind: 'instance', data: updated };
            }
            this._closeEditInstance();
        } catch (err) {
            alert(`Failed to update instance: ${err instanceof Error ? err.message : 'Unknown error'}`);
        } finally { this.editInstanceSubmitting = false; }
    }

    /* ── CSV/JSON Export ───────────────────────────────────────────────── */

    private _exportJSON(data: unknown[], filename: string) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
    }

    /* ── Filter Builder Methods ───────────────────────────────────────── */

    private _addFilterCondition() {
        this.filterConditions = [...this.filterConditions, {
            id: crypto.randomUUID(),
            field: '',
            operator: '=',
            value: '',
        }];
    }

    private _removeFilterCondition(id: string) {
        this.filterConditions = this.filterConditions.filter(c => c.id !== id);
    }

    private _updateFilterCondition(id: string, key: keyof FilterCondition, value: string) {
        this.filterConditions = this.filterConditions.map(c =>
            c.id === id ? { ...c, [key]: value } : c
        );
    }

    private _getFilterableProperties(): string[] {
        const props = new Set<string>();
        if (this.filterTargetType) {
            const type = this.types.find(t => t.id === this.filterTargetType);
            if (type?.properties) {
                type.properties.forEach(p => props.add(p.name));
            }
        }
        // Fallback: gather from existing instances
        if (props.size === 0) {
            this.objectInstances.forEach(inst => {
                Object.keys(inst.properties || {}).forEach(k => props.add(k));
            });
        }
        return [...props].sort();
    }

    private async _applyFilter() {
        if (!this.filterConditions.length) return;
        this.filterLoading = true;
        try {
            const params = new URLSearchParams();
            if (this.filterTargetType) params.set('object_type_id', this.filterTargetType);
            params.set('limit', '500');
            const all = await api.get<ObjectInstance[]>(`/ontology/objects?${params}`).catch(() => []);
            // Client-side filter (API may not support all operators)
            this.filterResults = all.filter(inst => {
                const checkFn = (c: FilterCondition): boolean => {
                    const val = inst.properties?.[c.field];
                    const strVal = String(val ?? '');
                    const strCmp = String(c.value ?? '');
                    switch (c.operator) {
                        case '=': return strVal === strCmp;
                        case '!=': return strVal !== strCmp;
                        case '>': return Number(val) > Number(c.value);
                        case '<': return Number(val) < Number(c.value);
                        case '>=': return Number(val) >= Number(c.value);
                        case '<=': return Number(val) <= Number(c.value);
                        case 'contains': return strVal.toLowerCase().includes(strCmp.toLowerCase());
                        case 'starts_with': return strVal.toLowerCase().startsWith(strCmp.toLowerCase());
                        case 'ends_with': return strVal.toLowerCase().endsWith(strCmp.toLowerCase());
                        default: return true;
                    }
                };
                return this.filterLogic === 'AND'
                    ? this.filterConditions.every(checkFn)
                    : this.filterConditions.some(checkFn);
            });
        } catch { this.filterResults = []; }
        finally { this.filterLoading = false; }
    }

    private _clearFilter() {
        this.filterConditions = [];
        this.filterResults = [];
        this.filterTargetType = '';
    }

    /* ── Type Builder Methods ─────────────────────────────────────────── */

    private _openTypeBuilder() {
        this.typeName = '';
        this.typeDescription = '';
        this.typeProperties = [];
        this.typeShowPreview = false;
        this.typeBuilderOpen = true;
    }

    private _closeTypeBuilder() { this.typeBuilderOpen = false; }

    private _addTypeProperty() {
        this.typeProperties = [...this.typeProperties, {
            name: '',
            property_type: 'string',
            required: false,
            default_value: '',
            validation_regex: '',
            validation_min: '',
            validation_max: '',
        }];
    }

    private _removeTypeProperty(idx: number) {
        this.typeProperties = this.typeProperties.filter((_, i) => i !== idx);
    }

    private _updateTypeProperty(idx: number, key: keyof TypePropertyForm, value: string | boolean) {
        this.typeProperties = this.typeProperties.map((p, i) => i === idx ? { ...p, [key]: value } : p);
    }

    private _typeSchemaPreview(): string {
        const props = this.typeProperties.filter(p => p.name).map(p => {
            const def: Record<string, unknown> = {
                name: p.name,
                property_type: p.property_type,
                required: p.required,
            };
            if (p.default_value) def.default_value = p.default_value;
            const rules: Record<string, unknown> = {};
            if (p.validation_regex) rules.regex = p.validation_regex;
            if (p.validation_min) rules.min = Number(p.validation_min);
            if (p.validation_max) rules.max = Number(p.validation_max);
            if (Object.keys(rules).length > 0) def.validation_rules = rules;
            return def;
        });
        return JSON.stringify({ name: this.typeName, description: this.typeDescription, properties: props }, null, 2);
    }

    private async _submitTypeBuilder() {
        if (!this.typeName.trim()) { alert('Type name is required'); return; }
        this.typeSubmitting = true;
        try {
            const properties = this.typeProperties.filter(p => p.name.trim()).map(p => {
                const prop: Record<string, unknown> = {
                    name: p.name,
                    property_type: p.property_type,
                    required: p.required,
                };
                if (p.default_value) prop.default_value = p.default_value;
                const rules: Record<string, unknown> = {};
                if (p.validation_regex) rules.regex = p.validation_regex;
                if (p.validation_min) rules.min = Number(p.validation_min);
                if (p.validation_max) rules.max = Number(p.validation_max);
                if (Object.keys(rules).length > 0) prop.validation_rules = rules;
                return prop;
            });
            await api.post('/ontology/types', { name: this.typeName, description: this.typeDescription, properties });
            this._closeTypeBuilder();
            await this._loadData();
        } catch (err) {
            alert(`Failed to create type: ${err instanceof Error ? err.message : 'Unknown error'}`);
        } finally { this.typeSubmitting = false; }
    }

    /* ── Action Builder Methods ───────────────────────────────────────── */

    private _openActionBuilder() {
        this.actionName = '';
        this.actionDescription = '';
        this.actionTargetType = '';
        this.actionParams = [];
        this.actionRules = [];
        this.actionSideEffects = [];
        this.actionUndoable = false;
        this.actionUndoRules = [];
        this.actionBuilderOpen = true;
    }

    private _closeActionBuilder() { this.actionBuilderOpen = false; }

    private _addActionParam() {
        this.actionParams = [...this.actionParams, { name: '', param_type: 'string', required: false, default_value: '' }];
    }

    private _removeActionParam(idx: number) {
        this.actionParams = this.actionParams.filter((_, i) => i !== idx);
    }

    private _updateActionParam(idx: number, key: keyof ActionParamForm, value: string | boolean) {
        this.actionParams = this.actionParams.map((p, i) => i === idx ? { ...p, [key]: value } : p);
    }

    private _addActionRule() {
        this.actionRules = [...this.actionRules, { rule_type: 'field_value', field: '', expected_value: '' }];
    }

    private _removeActionRule(idx: number) {
        this.actionRules = this.actionRules.filter((_, i) => i !== idx);
    }

    private _updateActionRule(idx: number, key: keyof ActionRuleForm, value: string) {
        this.actionRules = this.actionRules.map((r, i) => i === idx ? { ...r, [key]: value } : r);
    }

    private _addActionSideEffect() {
        this.actionSideEffects = [...this.actionSideEffects, { effect_type: 'webhook', url: '', channel: '' }];
    }

    private _removeActionSideEffect(idx: number) {
        this.actionSideEffects = this.actionSideEffects.filter((_, i) => i !== idx);
    }

    private _updateActionSideEffect(idx: number, key: keyof SideEffectForm, value: string) {
        this.actionSideEffects = this.actionSideEffects.map((s, i) => i === idx ? { ...s, [key]: value } : s);
    }

    private _addActionUndoRule() {
        this.actionUndoRules = [...this.actionUndoRules, { rule_type: 'field_revert', field: '' }];
    }

    private _removeActionUndoRule(idx: number) {
        this.actionUndoRules = this.actionUndoRules.filter((_, i) => i !== idx);
    }

    private _updateActionUndoRule(idx: number, key: keyof UndoRuleForm, value: string) {
        this.actionUndoRules = this.actionUndoRules.map((r, i) => i === idx ? { ...r, [key]: value } : r);
    }

    private async _submitActionBuilder() {
        if (!this.actionName.trim()) { alert('Action name is required'); return; }
        this.actionSubmitting = true;
        try {
            const targetId = this.actionTargetType || undefined;
            const payload: Record<string, unknown> = {
                name: this.actionName,
                description: this.actionDescription,
                parameters: this.actionParams.filter(p => p.name).map(p => ({
                    name: p.name,
                    type: p.param_type,
                    required: p.required,
                    ...(p.default_value ? { default: p.default_value } : {}),
                })),
                rules: this.actionRules.filter(r => r.field).map(r => ({
                    type: r.rule_type,
                    field: r.field,
                    expected_value: r.expected_value,
                })),
                side_effects: this.actionSideEffects.filter(s => s.effect_type).map(s => ({
                    type: s.effect_type,
                    ...(s.url ? { url: s.url } : {}),
                    ...(s.channel ? { channel: s.channel } : {}),
                })),
                undoable: this.actionUndoable,
                undo_rules: this.actionUndoRules.filter(r => r.field).map(r => ({
                    type: r.rule_type,
                    field: r.field,
                })),
            };
            if (targetId) payload.target_object_type = targetId;
            await api.post('/ontology/actions', payload);
            this._closeActionBuilder();
            alert('Action type created successfully');
        } catch (err) {
            alert(`Failed to create action: ${err instanceof Error ? err.message : 'Unknown error'}`);
        } finally { this.actionSubmitting = false; }
    }

    /* ── Function Editor Methods ──────────────────────────────────────── */

    private _openFunctionEditor() {
        this.functionName = '';
        this.functionDescription = '';
        this.functionLanguage = 'python';
        this.functionSourceCode = PYTHON_TEMPLATE;
        this.functionInputSchema = '{}';
        this.functionOutputSchema = '{}';
        this.functionOutput = '';
        this.functionError = '';
        this.functionEditorOpen = true;
    }

    private _closeFunctionEditor() { this.functionEditorOpen = false; }

    private _onFunctionCodeChange(e: CustomEvent) {
        this.functionSourceCode = e.detail.value;
    }

    private _onFunctionRun(e?: CustomEvent) {
        if (e) this.functionSourceCode = e.detail.value;
        this._runFunction();
    }

    private async _runFunction() {
        this.functionRunning = true;
        this.functionOutput = '';
        this.functionError = '';
        try {
            let inputSchema: Record<string, unknown> = {};
            try { inputSchema = JSON.parse(this.functionInputSchema); } catch { /* ignore */ }
            const result = await api.post<{ success?: boolean; output?: unknown; error?: string; duration_ms?: number }>(
                '/ontology/functions/run',
                {
                    source_code: this.functionSourceCode,
                    language: this.functionLanguage,
                    entry_point: 'handler',
                    input_data: inputSchema,
                }
            );
            this.functionOutput = typeof result?.output === 'string' ? result.output : JSON.stringify(result?.output, null, 2);
            if (result?.error) this.functionError = result.error;
            if (result?.duration_ms != null) this.functionOutput += `\n\n// Duration: ${result.duration_ms}ms`;
        } catch (err) {
            this.functionError = err instanceof Error ? err.message : 'Execution failed';
        } finally { this.functionRunning = false; }
    }

    private async _submitFunction() {
        if (!this.functionName.trim()) { alert('Function name is required'); return; }
        this.functionSubmitting = true;
        try {
            let inputSchema: Record<string, unknown> = {};
            let outputSchema: Record<string, unknown> = {};
            try { inputSchema = JSON.parse(this.functionInputSchema); } catch { /* ignore */ }
            try { outputSchema = JSON.parse(this.functionOutputSchema); } catch { /* ignore */ }
            await api.post('/ontology/functions', {
                name: this.functionName,
                description: this.functionDescription,
                language: this.functionLanguage,
                source_code: this.functionSourceCode,
                entry_point: 'handler',
                input_schema: inputSchema,
                output_schema: outputSchema,
            });
            this._closeFunctionEditor();
            alert('Function saved successfully');
        } catch (err) {
            alert(`Failed to save function: ${err instanceof Error ? err.message : 'Unknown error'}`);
        } finally { this.functionSubmitting = false; }
    }

    /* ── Graph helpers ─────────────────────────────────────────────────── */

    private _graphNodes() {
        const filtered = this._filterSearch(this.types);
        return filtered.map(t => ({
            id: t.id,
            label: t.name,
            type: 'object_type',
            size: Math.max(8, Math.min(24, (t.instance_count || 0) / 100 + 8)),
            data: t as unknown as Record<string, unknown>,
        }));
    }

    private _graphEdges() {
        const filteredIds = new Set(this._filterSearch(this.types).map(t => t.id));
        return this.links.map((l, i) => ({
            id: l.id || `link-${i}`,
            source: this.types.find(t => t.name === l.source_type)?.id || '',
            target: this.types.find(t => t.name === l.target_type)?.id || '',
            label: l.name,
        })).filter(e => e.source && e.target && (!this.searchQuery || filteredIds.has(e.source) || filteredIds.has(e.target)));
    }

    private _onNodeClick(e: CustomEvent) {
        const node = e.detail;
        this._openTypeDetail(node.data as ObjectType);
    }

    /* ── Table column definitions ──────────────────────────────────────── */

    private _objectTypeColumns() {
        return [
            { key: 'name', label: 'Name', sortable: true },
            { key: 'description', label: 'Description', sortable: true },
            { key: 'property_count', label: 'Properties', sortable: true, format: 'number' as const },
            { key: 'instance_count', label: 'Instances', sortable: true, format: 'number' as const },
            { key: 'version', label: 'Version', sortable: true },
            { key: 'created_at', label: 'Created', sortable: true, format: 'date' as const },
            { key: '_actions', label: 'Actions', sortable: false },
        ];
    }

    private _objectInstanceColumns(): Array<{ key: string; label: string; sortable?: boolean; format?: 'text' | 'number' | 'date' }> {
        const propKeys = new Set<string>();
        this.objectInstances.forEach(inst => {
            Object.keys(inst.properties || {}).forEach(k => propKeys.add(k));
        });
        const base: Array<{ key: string; label: string; sortable?: boolean; format?: 'text' | 'number' | 'date' }> = [
            { key: 'id', label: 'ID', sortable: false },
            { key: 'object_type_name', label: 'Type', sortable: true },
        ];
        const propCols = [...propKeys].slice(0, 10).map(k => ({
            key: `prop_${k}`,
            label: k,
            sortable: true,
        }));
        return [
            ...base,
            ...propCols,
            { key: 'version', label: 'Version', sortable: true },
            { key: 'created_at', label: 'Created', sortable: true, format: 'date' as const },
            { key: '_actions', label: 'Actions', sortable: false },
        ];
    }

    private _linkTypeColumns() {
        return [
            { key: 'name', label: 'Name', sortable: true },
            { key: 'source_type', label: 'Source Type', sortable: true },
            { key: 'target_type', label: 'Target Type', sortable: true },
            { key: 'cardinality', label: 'Cardinality', sortable: true },
            { key: 'instance_count', label: 'Instances', sortable: true, format: 'number' as const },
            { key: '_actions', label: 'Actions', sortable: false },
        ];
    }

    private _linkInstanceColumns() {
        return [
            { key: 'link_type_name', label: 'Link Type', sortable: true },
            { key: 'source_object', label: 'Source Object', sortable: false },
            { key: 'target_object', label: 'Target Object', sortable: false },
            { key: 'properties_summary', label: 'Properties', sortable: false },
            { key: '_actions', label: 'Actions', sortable: false },
        ];
    }

    /* ── Table row builders ────────────────────────────────────────────── */

    private _objectTypeRows() {
        return this._filterSearch(this.types).map(t => ({
            _id: t.id,
            name: t.name,
            description: t.description || '—',
            property_count: t.property_count,
            instance_count: t.instance_count,
            version: `v${t.version}`,
            created_at: t.created_at,
            _actions: '',
            _raw: t,
        }));
    }

    private _objectInstanceRows() {
        return this._filterSearch(this.objectInstances).map(inst => {
            const row: Record<string, unknown> = {
                _id: inst.id,
                id: inst.id.slice(0, 8) + '…',
                object_type_name: inst.object_type_name || inst.object_type,
                version: `v${inst.version}`,
                created_at: inst.created_at,
                _actions: '',
                _raw: inst,
            };
            Object.entries(inst.properties || {}).forEach(([k, v]) => {
                row[`prop_${k}`] = typeof v === 'object' ? JSON.stringify(v) : v;
            });
            return row;
        });
    }

    private _linkTypeRows() {
        return this._filterSearch(this.links).map(l => ({
            _id: l.id,
            name: l.name,
            source_type: l.source_type,
            target_type: l.target_type,
            cardinality: l.cardinality,
            instance_count: l.instance_count ?? 0,
            _actions: '',
        }));
    }

    private _linkInstanceRows() {
        return this._filterSearch(this.linkInstances).map(lk => ({
            _id: lk.id,
            link_type_name: lk.link_type_name,
            source_object: lk.source_object.slice(0, 8) + '…',
            target_object: lk.target_object.slice(0, 8) + '…',
            properties_summary: Object.keys(lk.properties || {}).length > 0
                ? Object.entries(lk.properties).map(([k, v]) => `${k}=${v}`).join(', ').slice(0, 60)
                : '—',
            _actions: '',
        }));
    }

    /* ── Render: Metrics Bar ───────────────────────────────────────────── */

    private _renderMetrics() {
        const totalInstances = this.types.reduce((s, t) => s + (t.instance_count || 0), 0);
        const totalProperties = this.types.reduce((s, t) => s + (t.property_count || 0), 0);

        return html`
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;padding:24px 32px">
            <voyant-metric-card label="Total Types" value="${this.types.length}" icon="📐" color="#FF4D00"></voyant-metric-card>
            <voyant-metric-card label="Total Links" value="${this.links.length}" icon="🔗" color="#3B82F6"></voyant-metric-card>
            <voyant-metric-card label="Total Properties" value="${totalProperties}" icon="🏷️" color="#8B5CF6"></voyant-metric-card>
            <voyant-metric-card label="Total Instances" value="${totalInstances.toLocaleString()}" icon="📦" color="#22C55E"></voyant-metric-card>
        </div>`;
    }

    /* ── Render: Search Bar ─────────────────────────────────────────────── */

    private _renderSearchBar() {
        return html`
        <div style="padding:0 32px 16px;display:flex;gap:12px;align-items:center" role="search" aria-label="Search ontology">
            <input
                type="text"
                class="voyant-input"
                placeholder="Search ${this.view === 'table' ? this.tableSubTab.replace(/-/g, ' ') : this.view === 'graph' ? 'graph nodes' : 'types'}..."
                aria-label="Search ${this.view === 'table' ? this.tableSubTab.replace(/-/g, ' ') : this.view === 'graph' ? 'graph nodes' : 'types'}"
                .value=${this.searchQuery}
                @input=${(e: Event) => { this.searchQuery = (e.target as HTMLInputElement).value; }}
                style="max-width:360px"
            />
            <span style="font-size:12px;color:var(--saas-text-muted)">${this.searchQuery ? 'Filtered' : 'Showing all'}</span>
        </div>`;
    }

    /* ── Render: Table Sub-Tabs ─────────────────────────────────────────── */

    private _renderTableSubTabs() {
        const tabs: Array<{ key: TableSubTab; label: string; icon: string; count: number }> = [
            { key: 'object-types', label: 'Object Types', icon: '📐', count: this.types.length },
            { key: 'object-instances', label: 'Object Instances', icon: '📦', count: this.objectInstances.length },
            { key: 'link-types', label: 'Link Types', icon: '🔗', count: this.links.length },
            { key: 'link-instances', label: 'Link Instances', icon: '⛓️', count: this.linkInstances.length },
        ];

        return html`
        <div style="display:flex;gap:2px;background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:var(--radius-lg);padding:3px;width:fit-content;margin:0 32px 16px" role="tablist" aria-label="Ontology data categories">
            ${tabs.map(t => html`
            <button
                class="voyant-tab ${this.tableSubTab === t.key ? 'active' : ''}"
                role="tab"
                aria-selected=${this.tableSubTab === t.key}
                @click=${() => this._switchTableTab(t.key)}
                style="font-size:12px"
            >${t.icon} ${t.label} <span style="font-size:10px;opacity:0.7;margin-left:4px">(${t.count})</span></button>
            `)}
        </div>`;
    }

    /* ── Render: Action Buttons Cell ───────────────────────────────────── */

    private _renderActionsCell(kind: 'type' | 'instance', data: any) {
        if (kind === 'type') {
            return html`
            <div style="display:flex;gap:4px">
                <button class="voyant-btn" style="font-size:11px;padding:3px 8px" @click=${(e: Event) => { e.stopPropagation(); this._openTypeDetail(data._raw || data); }}>✏️ Edit</button>
                <button class="voyant-btn" style="font-size:11px;padding:3px 8px;color:var(--saas-danger)" @click=${(e: Event) => { e.stopPropagation(); this._deleteType(data._id || data.id, data.name); }}>🗑️</button>
            </div>`;
        }
        return html`
        <div style="display:flex;gap:4px">
            <button class="voyant-btn" style="font-size:11px;padding:3px 8px" @click=${(e: Event) => { e.stopPropagation(); this._openInstanceDetail(data._raw || data); }}>👁️ View</button>
            <button class="voyant-btn" style="font-size:11px;padding:3px 8px;color:var(--saas-danger)" @click=${(e: Event) => { e.stopPropagation(); this._deleteInstance(data._id || data.id); }}>🗑️</button>
        </div>`;
    }

    /* ── Render: Table View ────────────────────────────────────────────── */

    private _renderTableView() {
        let columns: any[];
        let rows: any[];
        let title: string;
        let exportName: string;
        let actionKind: 'type' | 'instance';

        switch (this.tableSubTab) {
            case 'object-types':
                columns = this._objectTypeColumns();
                rows = this._objectTypeRows();
                title = 'Object Types';
                exportName = 'object-types';
                actionKind = 'type';
                break;
            case 'object-instances':
                columns = this._objectInstanceColumns();
                rows = this._objectInstanceRows();
                title = 'Object Instances';
                exportName = 'object-instances';
                actionKind = 'instance';
                break;
            case 'link-types':
                columns = this._linkTypeColumns();
                rows = this._linkTypeRows();
                title = 'Link Types';
                exportName = 'link-types';
                actionKind = 'type';
                break;
            case 'link-instances':
                columns = this._linkInstanceColumns();
                rows = this._linkInstanceRows();
                title = 'Link Instances';
                exportName = 'link-instances';
                actionKind = 'instance';
                break;
        }

        const isLoading = (this.tableSubTab === 'object-instances' && this.loadingInstances) ||
                           (this.tableSubTab === 'link-instances' && this.loadingLinkInstances);

        return html`
        <div style="padding:0 32px 32px">
            ${this._renderTableSubTabs()}

            <div class="voyant-card" style="padding:20px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <h3 style="font-size:14px;font-weight:600">${title}</h3>
                    <div style="display:flex;gap:8px">
                        <button class="voyant-btn" style="font-size:11px" @click=${() => {
                            const a = document.createElement('a');
                            a.href = URL.createObjectURL(new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' }));
                            a.download = `${exportName}.json`;
                            a.click();
                        }}>📥 JSON</button>
                        <button class="voyant-btn" style="font-size:11px" @click=${() => {
                            const headers = columns.filter(c => c.key !== '_actions').map(c => c.label).join(',');
                            const csvRows = rows.map(r => columns.filter(c => c.key !== '_actions').map(c => {
                                const v = r[c.key] ?? '';
                                return typeof v === 'string' && v.includes(',') ? `"${v}"` : String(v);
                            }).join(',')).join('\n');
                            const blob = new Blob([`${headers}\n${csvRows}`], { type: 'text/csv' });
                            const a = document.createElement('a');
                            a.href = URL.createObjectURL(blob);
                            a.download = `${exportName}.csv`;
                            a.click();
                        }}>📥 CSV</button>
                    </div>
                </div>

                ${isLoading ? html`<div style="text-align:center;padding:40px;color:var(--saas-text-muted)">Loading...</div>` : html`
                <voyant-data-table
                    .columns=${columns}
                    .rows=${rows}
                    .exportable=${false}
                    .filterable=${false}
                ></voyant-data-table>
                `}
            </div>
        </div>`;
    }

    /* ── Render: Grid View ─────────────────────────────────────────────── */

    private _renderGridView() {
        const filteredTypes = this._filterSearch(this.types);
        const getColor = (i: number) => {
            const colors = ['#FF4D00', '#3B82F6', '#22C55E', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#EF4444'];
            return colors[i % colors.length];
        };

        return html`
        <div style="padding:0 32px 32px">
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">
                ${filteredTypes.map((t, i) => {
                    const typeLinks = this.links.filter(l => l.source_type === t.name || l.target_type === t.name);
                    const color = getColor(i);
                    return html`
                    <div
                        class="voyant-card"
                        role="button"
                        tabindex="0"
                        aria-label="Object type: ${t.name}"
                        style="padding:20px;cursor:pointer;transition:all 0.2s cubic-bezier(0.4,0,0.2,1)"
                        @click=${() => this._openTypeDetail(t)}
                        @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._openTypeDetail(t); } }}
                        @mouseenter=${(e: Event) => {
                            const el = e.currentTarget as HTMLElement;
                            el.style.borderColor = color;
                            el.style.boxShadow = `0 4px 14px ${color}33`;
                        }}
                        @mouseleave=${(e: Event) => {
                            const el = e.currentTarget as HTMLElement;
                            el.style.borderColor = '';
                            el.style.boxShadow = '';
                        }}
                    >
                        <!-- Card Header -->
                        <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                            <div style="width:40px;height:40px;border-radius:10px;background:${color}15;display:flex;align-items:center;justify-content:center;font-size:18px;border:1px solid ${color}30">📐</div>
                            <div style="flex:1;min-width:0">
                                <div style="font-size:15px;font-weight:700;color:var(--saas-text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.name}</div>
                                <div style="font-size:11px;color:var(--saas-text-muted)">v${t.version} · ${t.tenant_id}</div>
                            </div>
                        </div>

                        <!-- Description -->
                        <p style="font-size:12px;color:var(--saas-text-secondary);margin-bottom:16px;min-height:32px;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${t.description || 'No description'}</p>

                        <!-- Stats -->
                        <div style="display:flex;gap:20px;font-size:11px;color:var(--saas-text-muted);margin-bottom:12px">
                            <div style="display:flex;align-items:center;gap:4px">
                                <span style="font-weight:700;font-size:16px;color:var(--saas-text-primary)">${t.property_count}</span>
                                <span>properties</span>
                            </div>
                            <div style="display:flex;align-items:center;gap:4px">
                                <span style="font-weight:700;font-size:16px;color:var(--saas-text-primary)">${(t.instance_count || 0).toLocaleString()}</span>
                                <span>instances</span>
                            </div>
                        </div>

                        <!-- Link Badges -->
                        <div style="display:flex;flex-wrap:wrap;gap:6px">
                            ${typeLinks.slice(0, 4).map(l => html`
                            <span style="font-size:10px;padding:3px 8px;border-radius:var(--radius-full);background:var(--saas-info-bg);color:var(--saas-info);font-weight:500">${l.name}</span>
                            `)}
                            ${typeLinks.length > 4 ? html`<span style="font-size:10px;padding:3px 8px;border-radius:var(--radius-full);background:var(--saas-bg-hover);color:var(--saas-text-muted)">+${typeLinks.length - 4} more</span>` : ''}
                            ${typeLinks.length === 0 ? html`<span style="font-size:10px;color:var(--saas-text-muted)">No links</span>` : ''}
                        </div>

                        <!-- Created Date -->
                        <div style="font-size:10px;color:var(--saas-text-muted);margin-top:12px;padding-top:12px;border-top:1px solid var(--saas-border)">
                            Created ${t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
                        </div>
                    </div>`;
                })}
                ${filteredTypes.length === 0 ? html`
                <div style="grid-column:1/-1;text-align:center;padding:80px;color:var(--saas-text-muted)">
                    ${this.searchQuery ? `No types match "${this.searchQuery}"` : 'No object types defined. Create your first type to start building your ontology.'}
                </div>` : ''}
            </div>
        </div>`;
    }

    /* ── Render: Detail Panel Content ───────────────────────────────────── */

    private _renderDetailContent() {
        if (!this.detailTarget) return html``;

        if (this.detailTarget.kind === 'type') {
            const t = this.detailTarget.data;
            return html`
            <!-- Detail Panel Tabs -->
            <div style="display:flex;gap:2px;background:var(--saas-bg-hover);border-radius:var(--radius-md);padding:3px;margin-bottom:16px">
                <button class="voyant-tab ${this.detailPanelTab === 'overview' ? 'active' : ''}" style="font-size:11px;padding:6px 12px;flex:1"
                    @click=${() => { this.detailPanelTab = 'overview'; }}>Overview</button>
                <button class="voyant-tab ${this.detailPanelTab === 'actions' ? 'active' : ''}" style="font-size:11px;padding:6px 12px;flex:1"
                    @click=${() => { this.detailPanelTab = 'actions'; }}>⚡ Actions <span style="font-size:9px;opacity:0.7">${this.typeActions.length}</span></button>
                <button class="voyant-tab ${this.detailPanelTab === 'functions' ? 'active' : ''}" style="font-size:11px;padding:6px 12px;flex:1"
                    @click=${() => { this.detailPanelTab = 'functions'; }}>💻 Functions <span style="font-size:9px;opacity:0.7">${this.typeFunctions.length}</span></button>
            </div>
            ${this.detailPanelTab === 'overview' ? this._renderTypeDetail(t) : ''}
            ${this.detailPanelTab === 'actions' ? this._renderTypeActionsTab(t) : ''}
            ${this.detailPanelTab === 'functions' ? this._renderTypeFunctionsTab(t) : ''}
            `;
        }
        return this._renderInstanceDetail(this.detailTarget.data);
    }

    private _renderTypeDetail(t: ObjectType) {
        const connectedLinks = this.links.filter(l => l.source_type === t.name || l.target_type === t.name);

        return html`
        <div style="font-family:Inter,system-ui,sans-serif">
            <!-- Description -->
            <p style="font-size:13px;color:var(--saas-text-secondary);margin-bottom:24px;line-height:1.5">${t.description || 'No description'}</p>

            <!-- Stats Grid -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px">
                <div style="padding:14px;border-radius:var(--radius-md);background:var(--saas-bg-hover)">
                    <div style="font-size:24px;font-weight:800;color:var(--saas-text-primary)">${t.property_count}</div>
                    <div style="font-size:11px;color:var(--saas-text-muted)">Properties</div>
                </div>
                <div style="padding:14px;border-radius:var(--radius-md);background:var(--saas-bg-hover)">
                    <div style="font-size:24px;font-weight:800;color:var(--saas-text-primary)">${(t.instance_count || 0).toLocaleString()}</div>
                    <div style="font-size:11px;color:var(--saas-text-muted)">Instances</div>
                </div>
                <div style="padding:14px;border-radius:var(--radius-md);background:var(--saas-bg-hover)">
                    <div style="font-size:24px;font-weight:800;color:var(--saas-text-primary)">${connectedLinks.length}</div>
                    <div style="font-size:11px;color:var(--saas-text-muted)">Link Types</div>
                </div>
                <div style="padding:14px;border-radius:var(--radius-md);background:var(--saas-bg-hover)">
                    <div style="font-size:24px;font-weight:800;color:var(--saas-text-primary)">v${t.version}</div>
                    <div style="font-size:11px;color:var(--saas-text-muted)">Version</div>
                </div>
            </div>

            <!-- Properties Table -->
            <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Properties</h4>
            <div style="margin-bottom:24px">
                ${this.detailProperties.length > 0 ? html`
                <table style="width:100%;border-collapse:collapse;font-size:12px" role="table" aria-label="Type properties">
                    <thead>
                        <tr style="border-bottom:1px solid var(--saas-border)">
                            <th style="padding:8px 0;text-align:left;font-weight:600;color:var(--saas-text-muted);font-size:11px">Name</th>
                            <th style="padding:8px 0;text-align:left;font-weight:600;color:var(--saas-text-muted);font-size:11px">Type</th>
                            <th style="padding:8px 0;text-align:center;font-weight:600;color:var(--saas-text-muted);font-size:11px">Required</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.detailProperties.map(p => html`
                        <tr style="border-bottom:1px solid var(--saas-border)">
                            <td style="padding:8px 0;color:var(--saas-text-primary);font-weight:500">${p.name}</td>
                            <td style="padding:8px 0"><span class="voyant-badge voyant-badge-info">${p.property_type}</span></td>
                            <td style="padding:8px 0;text-align:center">${p.required ? html`<span style="color:var(--saas-success)">✓</span>` : html`<span style="color:var(--saas-text-muted)">—</span>`}</td>
                        </tr>`)}
                    </tbody>
                </table>
                ` : html`
                <div style="font-size:12px;color:var(--saas-text-muted);padding:12px;text-align:center;background:var(--saas-bg-hover);border-radius:var(--radius-md)">
                    Loading properties...
                </div>`}
            </div>

            <!-- Connected Link Types -->
            <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Connected Links</h4>
            <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:24px">
                ${connectedLinks.map(l => html`
                <div style="display:flex;align-items:center;gap:8px;padding:10px;border-radius:var(--radius-md);border:1px solid var(--saas-border)">
                    <span style="font-size:14px">🔗</span>
                    <div style="flex:1">
                        <div style="font-size:12px;font-weight:600;color:var(--saas-text-primary)">${l.name}</div>
                        <div style="font-size:11px;color:var(--saas-text-muted)">${l.source_type} → ${l.target_type} · ${l.cardinality}</div>
                    </div>
                    <span class="voyant-badge voyant-badge-info">${l.instance_count ?? 0}</span>
                </div>`)}
                ${connectedLinks.length === 0 ? html`
                <div style="font-size:12px;color:var(--saas-text-muted);padding:12px;text-align:center">No links defined</div>` : ''}
            </div>

            <!-- Metadata -->
            <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Metadata</h4>
            <div style="font-size:12px;color:var(--saas-text-secondary);margin-bottom:24px">
                <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--saas-border)">
                    <span>Tenant ID</span><span style="font-family:monospace;font-size:11px">${t.tenant_id}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--saas-border)">
                    <span>Created</span><span>${t.created_at ? new Date(t.created_at).toLocaleString() : '—'}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:6px 0">
                    <span>Object ID</span><span style="font-family:monospace;font-size:11px">${t.id.slice(0, 12)}…</span>
                </div>
            </div>

            <!-- Actions -->
            <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Actions</h4>
            <div style="display:flex;flex-direction:column;gap:8px" role="group" aria-label="Type actions">
                <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center"
                    aria-label="View objects of type ${t.name}"
                    @click=${() => { this.view = 'table'; this.tableSubTab = 'object-instances'; this.selectedInstanceTypeId = t.id; this._loadObjectInstances(t.id); this._closeDetail(); }}>
                    📦 View Objects
                </button>
                <button class="voyant-btn" style="width:100%;justify-content:center"
                    aria-label="Edit type ${t.name}"
                    @click=${() => { this._editType(t); }}>
                    ✏️ Edit Type
                </button>
                <button class="voyant-btn" style="width:100%;justify-content:center"
                    aria-label="Create action for type ${t.name}"
                    @click=${() => { this.actionTargetType = t.id; this._openActionBuilder(); }}>
                    ⚡ Create Action
                </button>
                <button class="voyant-btn" style="width:100%;justify-content:center"
                    aria-label="Create function for type ${t.name}"
                    @click=${() => { this._openFunctionEditor(); }}>
                    💻 Create Function
                </button>
                <button class="voyant-btn" style="width:100%;justify-content:center;color:var(--saas-danger);border-color:var(--saas-danger)"
                    aria-label="Delete type ${t.name}"
                    @click=${() => this._deleteType(t.id, t.name)}>
                    🗑️ Delete Type
                </button>
            </div>
        </div>`;
    }

    private _renderTypeActionsTab(t: ObjectType) {
        return html`
        <div style="font-family:Inter,system-ui,sans-serif">
            <p style="font-size:13px;color:var(--saas-text-secondary);margin-bottom:16px">Actions define operations that can be performed on instances of <strong>${t.name}</strong>.</p>
            ${this.loadingActions ? html`<div style="text-align:center;padding:24px;color:var(--saas-text-muted)">Loading actions...</div>` : html`
            <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px">
                ${this.typeActions.length > 0 ? this.typeActions.map(a => html`
                <div style="padding:12px;border-radius:var(--radius-md);border:1px solid var(--saas-border)">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
                        <span style="font-size:13px;font-weight:600;color:var(--saas-text-primary)">${a.name}</span>
                        <span class="voyant-badge" style="font-size:10px;background:${a.status === 'active' ? 'var(--saas-success)' : 'var(--saas-text-muted)'};color:white">${a.status}</span>
                    </div>
                    <div style="font-size:11px;color:var(--saas-text-muted)">
                        ${a.parameters?.length || 0} params · ${a.rules ? 'rules' : 'no rules'} · ${a.undoable ? 'undoable' : 'not undoable'}
                    </div>
                </div>`) : html`
                <div style="font-size:12px;color:var(--saas-text-muted);padding:16px;text-align:center;background:var(--saas-bg-hover);border-radius:var(--radius-md)">
                    No actions defined yet
                </div>`}
            </div>
            <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center"
                @click=${() => { this.actionTargetType = t.id; this._openActionBuilder(); }}>
                ⚡ Create New Action
            </button>
            `}
        </div>`;
    }

    private _renderTypeFunctionsTab(t: ObjectType) {
        return html`
        <div style="font-family:Inter,system-ui,sans-serif">
            <p style="font-size:13px;color:var(--saas-text-secondary);margin-bottom:16px">Functions provide custom logic for <strong>${t.name}</strong> using Python or TypeScript.</p>
            ${this.loadingFunctions ? html`<div style="text-align:center;padding:24px;color:var(--saas-text-muted)">Loading functions...</div>` : html`
            <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px">
                ${this.typeFunctions.length > 0 ? this.typeFunctions.map(f => html`
                <div style="padding:12px;border-radius:var(--radius-md);border:1px solid var(--saas-border)">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
                        <span style="font-size:13px;font-weight:600;color:var(--saas-text-primary)">${f.name}</span>
                        <span style="font-size:10px;padding:2px 8px;border-radius:var(--radius-full);background:var(--saas-info-bg);color:var(--saas-info)">${f.language}</span>
                    </div>
                    <div style="font-size:11px;color:var(--saas-text-muted)">Entry: ${f.entry_point} · ${f.status}</div>
                    <div style="display:flex;gap:6px;margin-top:8px">
                        <button class="voyant-btn" style="font-size:11px;padding:3px 8px"
                            @click=${() => { this.funcEditorEditing = f; this.functionName = f.name; this.functionLanguage = f.language as 'python' | 'typescript'; this.functionSourceCode = f.source_code; this.functionInputSchema = JSON.stringify(f.input_schema || {}, null, 2); this.functionOutputSchema = JSON.stringify(f.output_schema || {}, null, 2); this.functionOutput = ''; this.functionError = ''; this.funcEditorOpen = true; }}>
                            ✏️ Edit
                        </button>
                        <button class="voyant-btn" style="font-size:11px;padding:3px 8px"
                            @click=${() => { this.functionSourceCode = f.source_code; this.functionLanguage = f.language as 'python' | 'typescript'; this._runFunction(); }}>
                            ▶️ Run
                        </button>
                    </div>
                </div>`) : html`
                <div style="font-size:12px;color:var(--saas-text-muted);padding:16px;text-align:center;background:var(--saas-bg-hover);border-radius:var(--radius-md)">
                    No functions defined yet
                </div>`}
            </div>
            <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center"
                @click=${() => { this.funcEditorEditing = null; this._openFunctionEditor(); }}>
                💻 Create New Function
            </button>
            `}
        </div>`;
    }

    private _renderInstanceDetail(inst: ObjectInstance) {
        const entries = Object.entries(inst.properties || {});
        const outLinks = this.linkInstances.filter(lk => lk.source_object === inst.id);
        const inLinks = this.linkInstances.filter(lk => lk.target_object === inst.id);

        return html`
        <div style="font-family:Inter,system-ui,sans-serif">
            <!-- Header Info -->
            <div style="display:flex;gap:8px;margin-bottom:16px">
                <span class="voyant-badge voyant-badge-info">${inst.object_type_name || inst.object_type}</span>
                <span class="voyant-badge" style="background:var(--saas-bg-hover);color:var(--saas-text-muted)">v${inst.version}</span>
            </div>

            <!-- Properties Form -->
            <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Properties</h4>
            <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:24px">
                ${entries.length > 0 ? entries.map(([key, value]) => html`
                <div style="padding:10px;border-radius:var(--radius-md);border:1px solid var(--saas-border)">
                    <div style="font-size:11px;font-weight:600;color:var(--saas-text-muted);margin-bottom:4px">${key}</div>
                    <div style="font-size:13px;color:var(--saas-text-primary);word-break:break-all">${typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—')}</div>
                </div>`) : html`
                <div style="font-size:12px;color:var(--saas-text-muted);text-align:center;padding:12px">No properties</div>`}
            </div>

            <!-- Outgoing Links -->
            <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Outgoing Links (${outLinks.length})</h4>
            <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:24px">
                ${outLinks.length > 0 ? outLinks.map(lk => html`
                <div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:var(--radius-md);border:1px solid var(--saas-border);font-size:12px">
                    <span style="color:var(--saas-info)">→</span>
                    <div style="flex:1">
                        <span style="font-weight:600">${lk.link_type_name}</span>
                        <span style="color:var(--saas-text-muted);margin-left:4px">→ ${lk.target_object.slice(0, 8)}…</span>
                    </div>
                </div>`) : html`
                <div style="font-size:12px;color:var(--saas-text-muted);text-align:center;padding:8px">No outgoing links</div>`}
            </div>

            <!-- Incoming Links -->
            <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Incoming Links (${inLinks.length})</h4>
            <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:24px">
                ${inLinks.length > 0 ? inLinks.map(lk => html`
                <div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:var(--radius-md);border:1px solid var(--saas-border);font-size:12px">
                    <span style="color:var(--saas-success)">←</span>
                    <div style="flex:1">
                        <span style="font-weight:600">${lk.link_type_name}</span>
                        <span style="color:var(--saas-text-muted);margin-left:4px">← ${lk.source_object.slice(0, 8)}…</span>
                    </div>
                </div>`) : html`
                <div style="font-size:12px;color:var(--saas-text-muted);text-align:center;padding:8px">No incoming links</div>`}
            </div>

            <!-- Metadata -->
            <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Audit Trail</h4>
            <div style="font-size:12px;color:var(--saas-text-secondary)">
                <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--saas-border)">
                    <span>Created</span><span>${inst.created_at ? new Date(inst.created_at).toLocaleString() : '—'}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--saas-border)">
                    <span>Tenant</span><span style="font-family:monospace;font-size:11px">${inst.tenant_id}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:6px 0">
                    <span>ID</span><span style="font-family:monospace;font-size:11px">${inst.id}</span>
                </div>
            </div>

            <!-- Actions -->
            <div style="margin-top:24px;display:flex;flex-direction:column;gap:8px">
                <button class="voyant-btn" style="width:100%;justify-content:center" @click=${() => this._openEditInstance(inst)}>✏️ Edit Instance</button>
                <button class="voyant-btn" style="width:100%;justify-content:center;color:var(--saas-danger);border-color:var(--saas-danger)" @click=${() => this._deleteInstance(inst.id)}>🗑️ Delete Instance</button>
            </div>
        </div>`;
    }

    /* ── Render: Filter Builder ────────────────────────────────────────── */

    private _renderFilterBuilder() {
        const properties = this._getFilterableProperties();
        const filterColumns = this.filterResults.length > 0
            ? Object.keys(this.filterResults[0]?.properties || {}).slice(0, 8).map(k => ({
                key: `prop_${k}`, label: k, sortable: true,
            }))
            : [];
        const tableColumns = [
            { key: 'id', label: 'ID', sortable: false },
            { key: 'object_type_name', label: 'Type', sortable: true },
            ...filterColumns,
            { key: 'created_at', label: 'Created', sortable: true, format: 'date' as const },
        ];
        const tableRows = this.filterResults.map(inst => {
            const row: Record<string, unknown> = {
                _id: inst.id,
                id: inst.id.slice(0, 8) + '…',
                object_type_name: inst.object_type_name || inst.object_type,
                created_at: inst.created_at,
            };
            Object.entries(inst.properties || {}).forEach(([k, v]) => {
                row[`prop_${k}`] = typeof v === 'object' ? JSON.stringify(v) : v;
            });
            return row;
        });

        return html`
        <div style="padding:0 32px 32px">
            <div class="voyant-card" style="padding:24px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
                    <h3 style="font-size:16px;font-weight:700">Filter Builder</h3>
                    <div style="display:flex;gap:8px">
                        <button class="voyant-btn-primary voyant-btn" style="font-size:12px" @click=${() => this._applyFilter()}>🔍 Apply Filter</button>
                        <button class="voyant-btn" style="font-size:12px" @click=${() => this._clearFilter()}>✕ Clear</button>
                    </div>
                </div>

                <!-- Target Type Selector -->
                <div style="margin-bottom:16px">
                    <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Target Type</label>
                    <select class="voyant-input" style="max-width:300px" .value=${this.filterTargetType}
                        @change=${(e: Event) => { this.filterTargetType = (e.target as HTMLSelectElement).value; this.filterResults = []; }}>
                        <option value="">All Types</option>
                        ${this.types.map(t => html`<option value=${t.id}>${t.name}</option>`)}
                    </select>
                </div>

                <!-- Logic Toggle -->
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:16px">
                    <span style="font-size:12px;font-weight:600;color:var(--saas-text-muted)">Logic:</span>
                    <button class="voyant-btn ${this.filterLogic === 'AND' ? 'active' : ''}" style="font-size:11px;padding:4px 12px"
                        @click=${() => { this.filterLogic = 'AND'; }}>AND</button>
                    <button class="voyant-btn ${this.filterLogic === 'OR' ? 'active' : ''}" style="font-size:11px;padding:4px 12px"
                        @click=${() => { this.filterLogic = 'OR'; }}>OR</button>
                </div>

                <!-- Conditions -->
                <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:16px">
                    ${this.filterConditions.map(c => html`
                    <div style="display:flex;gap:8px;align-items:center;padding:12px;border-radius:var(--radius-md);border:1px solid var(--saas-border);background:var(--saas-bg-hover)">
                        <select class="voyant-input" style="flex:2;font-size:12px" .value=${c.field}
                            @change=${(e: Event) => this._updateFilterCondition(c.id, 'field', (e.target as HTMLSelectElement).value)}>
                            <option value="">Select field...</option>
                            ${properties.map(p => html`<option value=${p} .selected=${c.field === p}>${p}</option>`)}
                        </select>
                        <select class="voyant-input" style="flex:1;font-size:12px" .value=${c.operator}
                            @change=${(e: Event) => this._updateFilterCondition(c.id, 'operator', (e.target as HTMLSelectElement).value)}>
                            ${FILTER_OPERATORS.map(op => html`<option value=${op} .selected=${c.operator === op}>${op}</option>`)}
                        </select>
                        <input class="voyant-input" style="flex:2;font-size:12px" placeholder="Value" .value=${c.value}
                            @input=${(e: Event) => this._updateFilterCondition(c.id, 'value', (e.target as HTMLInputElement).value)} />
                        <button style="background:none;border:none;color:var(--saas-danger);cursor:pointer;font-size:16px;padding:4px 8px"
                            @click=${() => this._removeFilterCondition(c.id)}>✕</button>
                    </div>`)}
                    <button class="voyant-btn" style="font-size:12px;align-self:flex-start" @click=${() => this._addFilterCondition()}>+ Add Condition</button>
                </div>

                ${this.filterConditions.length === 0 ? html`
                <div style="text-align:center;padding:40px;color:var(--saas-text-muted);font-size:13px">
                    Add conditions above and click "Apply Filter" to query your ontology data.
                </div>` : ''}

                <!-- Results -->
                ${this.filterResults.length > 0 ? html`
                <div style="margin-top:20px;border-top:1px solid var(--saas-border);padding-top:20px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                        <h4 style="font-size:14px;font-weight:600">Results (${this.filterResults.length})</h4>
                    </div>
                    <voyant-data-table .columns=${tableColumns} .rows=${tableRows} .exportable=${true} .filterable=${false}></voyant-data-table>
                </div>` : ''}

                ${this.filterLoading ? html`<div style="text-align:center;padding:20px;color:var(--saas-text-muted)">Filtering...</div>` : ''}
            </div>
        </div>`;
    }

    /* ── Render: Type Builder Modal ────────────────────────────────────── */

    private _renderTypeBuilderModal() {
        if (!this.typeBuilderOpen) return html``;
        return html`
        <div style="position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center" role="dialog" aria-modal="true" aria-label="Create object type"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this._closeTypeBuilder(); }}>
            <div style="position:fixed;inset:0;background:rgba(0,0,0,0.5)" @click=${() => this._closeTypeBuilder()}></div>
            <div style="position:relative;width:780px;max-height:85vh;background:var(--saas-bg-card);border-radius:var(--radius-lg);border:1px solid var(--saas-border);box-shadow:0 24px 48px rgba(0,0,0,0.3);overflow-y:auto;z-index:1" tabindex="-1">
                <!-- Header -->
                <div style="display:flex;align-items:center;justify-content:space-between;padding:20px 24px;border-bottom:1px solid var(--saas-border);position:sticky;top:0;background:var(--saas-bg-card);z-index:1">
                    <h3 style="font-size:16px;font-weight:700">Create Object Type</h3>
                    <button style="background:none;border:none;color:var(--saas-text-muted);cursor:pointer;font-size:18px" aria-label="Close create type dialog" @click=${() => this._closeTypeBuilder()}>✕</button>
                </div>

                <div style="padding:24px">
                    <!-- Basic Info -->
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px">
                        <div>
                            <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Name *</label>
                            <input class="voyant-input" style="width:100%" placeholder="e.g. Customer" .value=${this.typeName}
                                @input=${(e: Event) => { this.typeName = (e.target as HTMLInputElement).value; }} />
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Description</label>
                            <input class="voyant-input" style="width:100%" placeholder="Description..." .value=${this.typeDescription}
                                @input=${(e: Event) => { this.typeDescription = (e.target as HTMLInputElement).value; }} />
                        </div>
                    </div>

                    <!-- Properties Palette -->
                    <div style="margin-bottom:24px">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                            <h4 style="font-size:13px;font-weight:600">Properties (${this.typeProperties.length})</h4>
                            <button class="voyant-btn" style="font-size:11px" @click=${() => this._addTypeProperty()}>+ Add Property</button>
                        </div>

                        <div style="display:flex;flex-direction:column;gap:8px">
                            ${this.typeProperties.map((p, i) => html`
                            <div style="display:flex;gap:8px;align-items:center;padding:12px;border-radius:var(--radius-md);border:1px solid var(--saas-border);background:var(--saas-bg-hover)">
                                <input class="voyant-input" style="flex:2;font-size:12px" placeholder="Property name" .value=${p.name}
                                    @input=${(e: Event) => this._updateTypeProperty(i, 'name', (e.target as HTMLInputElement).value)} />
                                <select class="voyant-input" style="flex:1.5;font-size:12px" .value=${p.property_type}
                                    @change=${(e: Event) => this._updateTypeProperty(i, 'property_type', (e.target as HTMLSelectElement).value)}>
                                    ${PROPERTY_TYPES.map(t => html`<option value=${t}>${t}</option>`)}
                                </select>
                                <label style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--saas-text-muted);white-space:nowrap">
                                    <input type="checkbox" .checked=${p.required}
                                        @change=${(e: Event) => this._updateTypeProperty(i, 'required', (e.target as HTMLInputElement).checked)} />
                                    Req
                                </label>
                                <input class="voyant-input" style="flex:1;font-size:11px" placeholder="Default" .value=${p.default_value}
                                    @input=${(e: Event) => this._updateTypeProperty(i, 'default_value', (e.target as HTMLInputElement).value)} />
                                <button style="background:none;border:none;color:var(--saas-danger);cursor:pointer;font-size:14px;padding:4px"
                                    @click=${() => this._removeTypeProperty(i)}>✕</button>
                            </div>

                            <!-- Validation row -->
                            ${p.property_type === 'string' || p.property_type === 'integer' || p.property_type === 'float' ? html`
                            <div style="display:flex;gap:8px;padding:0 12px 8px">
                                ${p.property_type === 'string' ? html`
                                <input class="voyant-input" style="flex:1;font-size:11px" placeholder="Regex validation" .value=${p.validation_regex}
                                    @input=${(e: Event) => this._updateTypeProperty(i, 'validation_regex', (e.target as HTMLInputElement).value)} />
                                ` : ''}
                                ${p.property_type === 'integer' || p.property_type === 'float' ? html`
                                <input class="voyant-input" style="flex:1;font-size:11px" placeholder="Min" .value=${p.validation_min}
                                    @input=${(e: Event) => this._updateTypeProperty(i, 'validation_min', (e.target as HTMLInputElement).value)} />
                                <input class="voyant-input" style="flex:1;font-size:11px" placeholder="Max" .value=${p.validation_max}
                                    @input=${(e: Event) => this._updateTypeProperty(i, 'validation_max', (e.target as HTMLInputElement).value)} />
                                ` : ''}
                            </div>` : ''}
                            `)}
                            ${this.typeProperties.length === 0 ? html`
                            <div style="text-align:center;padding:24px;color:var(--saas-text-muted);font-size:12px;border:1px dashed var(--saas-border);border-radius:var(--radius-md)">
                                No properties yet. Click "Add Property" to define the schema.
                            </div>` : ''}
                        </div>
                    </div>

                    <!-- JSON Preview -->
                    <div style="margin-bottom:24px">
                        <button class="voyant-btn" style="font-size:11px;margin-bottom:8px"
                            @click=${() => { this.typeShowPreview = !this.typeShowPreview; }}>
                            ${this.typeShowPreview ? 'Hide' : 'Show'} JSON Schema Preview
                        </button>
                        ${this.typeShowPreview ? html`
                        <pre style="background:var(--saas-bg-hover);padding:16px;border-radius:var(--radius-md);font-size:12px;font-family:monospace;overflow-x:auto;max-height:300px;border:1px solid var(--saas-border)">${this._typeSchemaPreview()}</pre>
                        ` : ''}
                    </div>

                    <!-- Actions -->
                    <div style="display:flex;gap:8px;justify-content:flex-end">
                        <button class="voyant-btn" @click=${() => this._closeTypeBuilder()}>Cancel</button>
                        <button class="voyant-btn-primary voyant-btn" @click=${() => this._submitTypeBuilder()} .disabled=${this.typeSubmitting}>
                            ${this.typeSubmitting ? 'Creating...' : 'Create Type'}
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    /* ── Render: Action Builder Modal ──────────────────────────────────── */

    private _renderActionBuilderModal() {
        if (!this.actionBuilderOpen) return html``;
        return html`
        <div style="position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center" role="dialog" aria-modal="true" aria-label="Create action type"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this._closeActionBuilder(); }}>
            <div style="position:fixed;inset:0;background:rgba(0,0,0,0.5)" @click=${() => this._closeActionBuilder()}></div>
            <div style="position:relative;width:800px;max-height:85vh;background:var(--saas-bg-card);border-radius:var(--radius-lg);border:1px solid var(--saas-border);box-shadow:0 24px 48px rgba(0,0,0,0.3);overflow-y:auto;z-index:1" tabindex="-1">
                <!-- Header -->
                <div style="display:flex;align-items:center;justify-content:space-between;padding:20px 24px;border-bottom:1px solid var(--saas-border);position:sticky;top:0;background:var(--saas-bg-card);z-index:1">
                    <h3 style="font-size:16px;font-weight:700">Create Action Type</h3>
                    <button style="background:none;border:none;color:var(--saas-text-muted);cursor:pointer;font-size:18px" aria-label="Close create action dialog" @click=${() => this._closeActionBuilder()}>✕</button>
                </div>

                <div style="padding:24px">
                    <!-- Basic Info -->
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
                        <div>
                            <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Name *</label>
                            <input class="voyant-input" style="width:100%" placeholder="e.g. assign_ticket" .value=${this.actionName}
                                @input=${(e: Event) => { this.actionName = (e.target as HTMLInputElement).value; }} />
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Description</label>
                            <input class="voyant-input" style="width:100%" placeholder="Description..." .value=${this.actionDescription}
                                @input=${(e: Event) => { this.actionDescription = (e.target as HTMLInputElement).value; }} />
                        </div>
                    </div>

                    <div style="margin-bottom:20px">
                        <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Target Object Type</label>
                        <select class="voyant-input" style="max-width:300px" .value=${this.actionTargetType}
                            @change=${(e: Event) => { this.actionTargetType = (e.target as HTMLSelectElement).value; }}>
                            <option value="">None (global)</option>
                            ${this.types.map(t => html`<option value=${t.id}>${t.name}</option>`)}
                        </select>
                    </div>

                    <!-- Parameters -->
                    <div style="margin-bottom:20px">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                            <h4 style="font-size:13px;font-weight:600">Parameters (${this.actionParams.length})</h4>
                            <button class="voyant-btn" style="font-size:11px" @click=${() => this._addActionParam()}>+ Add Parameter</button>
                        </div>
                        ${this.actionParams.map((p, i) => html`
                        <div style="display:flex;gap:8px;align-items:center;padding:8px;margin-bottom:6px;border:1px solid var(--saas-border);border-radius:var(--radius-md);background:var(--saas-bg-hover)">
                            <input class="voyant-input" style="flex:2;font-size:12px" placeholder="Name" .value=${p.name}
                                @input=${(e: Event) => this._updateActionParam(i, 'name', (e.target as HTMLInputElement).value)} />
                            <select class="voyant-input" style="flex:1;font-size:12px" .value=${p.param_type}
                                @change=${(e: Event) => this._updateActionParam(i, 'param_type', (e.target as HTMLSelectElement).value)}>
                                ${PARAM_TYPES.map(t => html`<option value=${t}>${t}</option>`)}
                            </select>
                            <label style="display:flex;align-items:center;gap:4px;font-size:11px;white-space:nowrap">
                                <input type="checkbox" .checked=${p.required}
                                    @change=${(e: Event) => this._updateActionParam(i, 'required', (e.target as HTMLInputElement).checked)} /> Req
                            </label>
                            <input class="voyant-input" style="flex:1;font-size:11px" placeholder="Default" .value=${p.default_value}
                                @input=${(e: Event) => this._updateActionParam(i, 'default_value', (e.target as HTMLInputElement).value)} />
                            <button style="background:none;border:none;color:var(--saas-danger);cursor:pointer;font-size:14px" @click=${() => this._removeActionParam(i)}>✕</button>
                        </div>`)}
                    </div>

                    <!-- Rules (Pre-conditions) -->
                    <div style="margin-bottom:20px">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                            <h4 style="font-size:13px;font-weight:600">Pre-condition Rules (${this.actionRules.length})</h4>
                            <button class="voyant-btn" style="font-size:11px" @click=${() => this._addActionRule()}>+ Add Rule</button>
                        </div>
                        ${this.actionRules.map((r, i) => html`
                        <div style="display:flex;gap:8px;align-items:center;padding:8px;margin-bottom:6px;border:1px solid var(--saas-border);border-radius:var(--radius-md);background:var(--saas-bg-hover)">
                            <select class="voyant-input" style="flex:1;font-size:12px" .value=${r.rule_type}
                                @change=${(e: Event) => this._updateActionRule(i, 'rule_type', (e.target as HTMLSelectElement).value)}>
                                ${RULE_TYPES.map(t => html`<option value=${t}>${t}</option>`)}
                            </select>
                            <input class="voyant-input" style="flex:1;font-size:12px" placeholder="Field" .value=${r.field}
                                @input=${(e: Event) => this._updateActionRule(i, 'field', (e.target as HTMLInputElement).value)} />
                            <input class="voyant-input" style="flex:1;font-size:12px" placeholder="Expected value" .value=${r.expected_value}
                                @input=${(e: Event) => this._updateActionRule(i, 'expected_value', (e.target as HTMLInputElement).value)} />
                            <button style="background:none;border:none;color:var(--saas-danger);cursor:pointer;font-size:14px" @click=${() => this._removeActionRule(i)}>✕</button>
                        </div>`)}
                    </div>

                    <!-- Side Effects -->
                    <div style="margin-bottom:20px">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                            <h4 style="font-size:13px;font-weight:600">Side Effects (${this.actionSideEffects.length})</h4>
                            <button class="voyant-btn" style="font-size:11px" @click=${() => this._addActionSideEffect()}>+ Add Side Effect</button>
                        </div>
                        ${this.actionSideEffects.map((s, i) => html`
                        <div style="display:flex;gap:8px;align-items:center;padding:8px;margin-bottom:6px;border:1px solid var(--saas-border);border-radius:var(--radius-md);background:var(--saas-bg-hover)">
                            <select class="voyant-input" style="flex:1;font-size:12px" .value=${s.effect_type}
                                @change=${(e: Event) => this._updateActionSideEffect(i, 'effect_type', (e.target as HTMLSelectElement).value)}>
                                ${SIDE_EFFECT_TYPES.map(t => html`<option value=${t}>${t}</option>`)}
                            </select>
                            ${s.effect_type === 'webhook' ? html`
                            <input class="voyant-input" style="flex:2;font-size:12px" placeholder="Webhook URL" .value=${s.url}
                                @input=${(e: Event) => this._updateActionSideEffect(i, 'url', (e.target as HTMLInputElement).value)} />
                            ` : ''}
                            ${s.effect_type === 'notification' ? html`
                            <input class="voyant-input" style="flex:2;font-size:12px" placeholder="Notification channel" .value=${s.channel}
                                @input=${(e: Event) => this._updateActionSideEffect(i, 'channel', (e.target as HTMLInputElement).value)} />
                            ` : ''}
                            ${s.effect_type === 'audit_log' || s.effect_type === 'field_update' ? html`
                            <span style="flex:2;font-size:12px;color:var(--saas-text-muted)">Auto-configured</span>
                            ` : ''}
                            <button style="background:none;border:none;color:var(--saas-danger);cursor:pointer;font-size:14px" @click=${() => this._removeActionSideEffect(i)}>✕</button>
                        </div>`)}
                    </div>

                    <!-- Undo Config -->
                    <div style="margin-bottom:24px;padding:16px;border:1px solid var(--saas-border);border-radius:var(--radius-md)">
                        <label style="display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;margin-bottom:12px">
                            <input type="checkbox" .checked=${this.actionUndoable}
                                @change=${(e: Event) => { this.actionUndoable = (e.target as HTMLInputElement).checked; }} />
                            Enable Undo
                        </label>
                        ${this.actionUndoable ? html`
                        <div style="margin-top:8px">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                                <span style="font-size:12px;color:var(--saas-text-muted)">Undo Rules (${this.actionUndoRules.length})</span>
                                <button class="voyant-btn" style="font-size:11px" @click=${() => this._addActionUndoRule()}>+ Add Undo Rule</button>
                            </div>
                            ${this.actionUndoRules.map((r, i) => html`
                            <div style="display:flex;gap:8px;align-items:center;padding:6px;margin-bottom:4px">
                                <select class="voyant-input" style="flex:1;font-size:12px" .value=${r.rule_type}
                                    @change=${(e: Event) => this._updateActionUndoRule(i, 'rule_type', (e.target as HTMLSelectElement).value)}>
                                    ${UNDO_RULE_TYPES.map(t => html`<option value=${t}>${t}</option>`)}
                                </select>
                                <input class="voyant-input" style="flex:1;font-size:12px" placeholder="Field" .value=${r.field}
                                    @input=${(e: Event) => this._updateActionUndoRule(i, 'field', (e.target as HTMLInputElement).value)} />
                                <button style="background:none;border:none;color:var(--saas-danger);cursor:pointer;font-size:14px" @click=${() => this._removeActionUndoRule(i)}>✕</button>
                            </div>`)}
                        </div>` : ''}
                    </div>

                    <!-- Actions -->
                    <div style="display:flex;gap:8px;justify-content:flex-end">
                        <button class="voyant-btn" @click=${() => this._closeActionBuilder()}>Cancel</button>
                        <button class="voyant-btn-primary voyant-btn" @click=${() => this._submitActionBuilder()} .disabled=${this.actionSubmitting}>
                            ${this.actionSubmitting ? 'Creating...' : 'Create Action'}
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    /* ── Render: Function Editor Modal ─────────────────────────────────── */

    private _renderFunctionEditorModal() {
        if (!this.functionEditorOpen) return html``;
        return html`
        <div style="position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center" role="dialog" aria-modal="true" aria-label="Function editor"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this._closeFunctionEditor(); }}>
            <div style="position:fixed;inset:0;background:rgba(0,0,0,0.5)" @click=${() => this._closeFunctionEditor()}></div>
            <div style="position:relative;width:900px;max-height:90vh;background:var(--saas-bg-card);border-radius:var(--radius-lg);border:1px solid var(--saas-border);box-shadow:0 24px 48px rgba(0,0,0,0.3);display:flex;flex-direction:column;z-index:1" tabindex="-1">
                <!-- Header -->
                <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 24px;border-bottom:1px solid var(--saas-border)">
                    <h3 style="font-size:16px;font-weight:700">Function Editor</h3>
                    <div style="display:flex;gap:8px;align-items:center">
                        <select class="voyant-input" style="font-size:12px;width:140px" .value=${this.functionLanguage}
                            @change=${(e: Event) => {
                                const lang = (e.target as HTMLSelectElement).value as 'python' | 'typescript';
                                this.functionLanguage = lang;
                                if (!this.functionSourceCode || this.functionSourceCode === PYTHON_TEMPLATE || this.functionSourceCode === TYPESCRIPT_TEMPLATE) {
                                    this.functionSourceCode = lang === 'python' ? PYTHON_TEMPLATE : TYPESCRIPT_TEMPLATE;
                                }
                            }}>
                            <option value="python">Python</option>
                            <option value="typescript">TypeScript</option>
                        </select>
                        <button class="voyant-btn" style="font-size:11px" @click=${() => this._closeFunctionEditor()}>✕</button>
                    </div>
                </div>

                <div style="display:flex;flex:1;overflow:hidden">
                    <!-- Left: Config + Editor -->
                    <div style="flex:3;display:flex;flex-direction:column;overflow:hidden">
                        <!-- Function Name / Description -->
                        <div style="display:flex;gap:8px;padding:12px 16px;border-bottom:1px solid var(--saas-border)">
                            <input class="voyant-input" style="flex:1;font-size:12px" placeholder="Function name" .value=${this.functionName}
                                @input=${(e: Event) => { this.functionName = (e.target as HTMLInputElement).value; }} />
                            <input class="voyant-input" style="flex:1;font-size:12px" placeholder="Description" .value=${this.functionDescription}
                                @input=${(e: Event) => { this.functionDescription = (e.target as HTMLInputElement).value; }} />
                        </div>

                        <!-- Monaco Editor -->
                        <div style="flex:1;min-height:300px">
                            <voyant-monaco-editor
                                .language=${this.functionLanguage === 'python' ? 'python' : 'typescript'}
                                .value=${this.functionSourceCode}
                                .height=${'100%'}
                                @change=${(e: CustomEvent) => this._onFunctionCodeChange(e)}
                                @run=${(e: CustomEvent) => this._onFunctionRun(e)}
                            ></voyant-monaco-editor>
                        </div>

                        <!-- Run bar -->
                        <div style="display:flex;gap:8px;padding:10px 16px;border-top:1px solid var(--saas-border);align-items:center">
                            <button class="voyant-btn-primary voyant-btn" style="font-size:12px" @click=${() => this._runFunction()} .disabled=${this.functionRunning}>
                                ${this.functionRunning ? '⏳ Running...' : '▶ Run (Ctrl+Enter)'}
                            </button>
                            <span style="font-size:11px;color:var(--saas-text-muted)">Press Ctrl+Enter in editor to run</span>
                        </div>
                    </div>

                    <!-- Right: Schemas + Output -->
                    <div style="flex:1;min-width:240px;border-left:1px solid var(--saas-border);display:flex;flex-direction:column;overflow-y:auto">
                        <!-- Input Schema -->
                        <div style="padding:12px;border-bottom:1px solid var(--saas-border)">
                            <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Input Schema (JSON)</label>
                            <textarea class="voyant-input" style="width:100%;height:60px;font-size:11px;font-family:monospace;resize:vertical" .value=${this.functionInputSchema}
                                @input=${(e: Event) => { this.functionInputSchema = (e.target as HTMLTextAreaElement).value; }}></textarea>
                        </div>

                        <!-- Output Schema -->
                        <div style="padding:12px;border-bottom:1px solid var(--saas-border)">
                            <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Output Schema (JSON)</label>
                            <textarea class="voyant-input" style="width:100%;height:60px;font-size:11px;font-family:monospace;resize:vertical" .value=${this.functionOutputSchema}
                                @input=${(e: Event) => { this.functionOutputSchema = (e.target as HTMLTextAreaElement).value; }}></textarea>
                        </div>

                        <!-- Output Panel -->
                        <div style="flex:1;padding:12px">
                            <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:6px">Output</label>
                            ${this.functionError ? html`
                            <pre style="background:#1a0000;color:#ef4444;padding:10px;border-radius:6px;font-size:11px;font-family:monospace;max-height:200px;overflow:auto;white-space:pre-wrap">${this.functionError}</pre>
                            ` : this.functionOutput ? html`
                            <pre style="background:var(--saas-bg-hover);padding:10px;border-radius:6px;font-size:11px;font-family:monospace;max-height:200px;overflow:auto;white-space:pre-wrap">${this.functionOutput}</pre>
                            ` : html`
                            <div style="font-size:11px;color:var(--saas-text-muted);padding:20px;text-align:center">Run the function to see output</div>
                            `}
                        </div>

                        <!-- Save button -->
                        <div style="padding:12px;border-top:1px solid var(--saas-border)">
                            <button class="voyant-btn-primary voyant-btn" style="width:100%;font-size:12px;justify-content:center"
                                @click=${() => this._submitFunction()} .disabled=${this.functionSubmitting}>
                                ${this.functionSubmitting ? 'Saving...' : '💾 Save Function'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    }

    /* ── Render: Edit Instance Modal ────────────────────────────────────── */

    private _renderEditInstanceModal() {
        if (!this.editInstanceOpen || !this.editInstanceData) return html``;
        const inst = this.editInstanceData;
        const entries = Object.entries(this.editInstanceProps);
        return html`
        <div style="position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center" role="dialog" aria-modal="true" aria-label="Edit instance"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this._closeEditInstance(); }}>
            <div style="position:fixed;inset:0;background:rgba(0,0,0,0.5)" @click=${() => this._closeEditInstance()}></div>
            <div style="position:relative;width:600px;max-height:80vh;background:var(--saas-bg-card);border-radius:var(--radius-lg);border:1px solid var(--saas-border);box-shadow:0 24px 48px rgba(0,0,0,0.3);overflow-y:auto;z-index:1" tabindex="-1">
                <!-- Header -->
                <div style="display:flex;align-items:center;justify-content:space-between;padding:20px 24px;border-bottom:1px solid var(--saas-border);position:sticky;top:0;background:var(--saas-bg-card);z-index:1">
                    <h3 style="font-size:16px;font-weight:700">Edit Instance</h3>
                    <button style="background:none;border:none;color:var(--saas-text-muted);cursor:pointer;font-size:18px" aria-label="Close edit instance dialog" @click=${() => this._closeEditInstance()}>✕</button>
                </div>
                <div style="padding:24px">
                    <div style="display:flex;gap:8px;margin-bottom:16px">
                        <span class="voyant-badge voyant-badge-info">${inst.object_type_name || inst.object_type}</span>
                        <span class="voyant-badge" style="background:var(--saas-bg-hover);color:var(--saas-text-muted)">v${inst.version}</span>
                        <span style="font-family:monospace;font-size:11px;color:var(--saas-text-muted)">${inst.id.slice(0, 12)}…</span>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:24px">
                        ${entries.map(([key, value]) => html`
                        <div>
                            <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">${key}</label>
                            <input class="voyant-input" style="width:100%;font-size:12px" .value=${value}
                                @input=${(e: Event) => this._updateEditInstanceProp(key, (e.target as HTMLInputElement).value)} />
                        </div>`)}
                        ${entries.length === 0 ? html`
                        <div style="font-size:12px;color:var(--saas-text-muted);text-align:center;padding:16px">No properties to edit</div>` : ''}
                    </div>
                    <div style="display:flex;gap:8px;justify-content:flex-end">
                        <button class="voyant-btn" @click=${() => this._closeEditInstance()}>Cancel</button>
                        <button class="voyant-btn-primary voyant-btn" @click=${() => this._submitEditInstance()} .disabled=${this.editInstanceSubmitting}>
                            ${this.editInstanceSubmitting ? 'Saving...' : '💾 Save Changes'}
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    /* ── Render: Builders Tab ──────────────────────────────────────────── */

    private _renderBuildersView() {
        return html`
        <div style="padding:0 32px 32px">
            <!-- Builder Cards -->
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;margin-bottom:24px">

                <!-- Filter Builder Card -->
                <div class="voyant-card" style="padding:24px;cursor:pointer;transition:all 0.2s"
                    @click=${() => { this._addFilterCondition(); this._loadObjectInstances(); }}>
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                        <div style="width:44px;height:44px;border-radius:10px;background:#3B82F615;display:flex;align-items:center;justify-content:center;font-size:20px;border:1px solid #3B82F630">🔍</div>
                        <div>
                            <div style="font-size:15px;font-weight:700">Filter Builder</div>
                            <div style="font-size:12px;color:var(--saas-text-muted)">Visual query condition editor</div>
                        </div>
                    </div>
                    <p style="font-size:12px;color:var(--saas-text-secondary);line-height:1.5">Build complex filters with AND/OR logic across ontology properties. Apply to any object type.</p>
                </div>

                <!-- Type Builder Card -->
                <div class="voyant-card" style="padding:24px;cursor:pointer;transition:all 0.2s"
                    @click=${() => this._openTypeBuilder()}>
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                        <div style="width:44px;height:44px;border-radius:10px;background:#FF4D0015;display:flex;align-items:center;justify-content:center;font-size:20px;border:1px solid #FF4D0030">📐</div>
                        <div>
                            <div style="font-size:15px;font-weight:700">Type Builder</div>
                            <div style="font-size:12px;color:var(--saas-text-muted)">Create object types with schema</div>
                        </div>
                    </div>
                    <p style="font-size:12px;color:var(--saas-text-secondary);line-height:1.5">Define types with properties, validation rules, required fields, and preview JSON schema before creating.</p>
                </div>

                <!-- Action Builder Card -->
                <div class="voyant-card" style="padding:24px;cursor:pointer;transition:all 0.2s"
                    @click=${() => this._openActionBuilder()}>
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                        <div style="width:44px;height:44px;border-radius:10px;background:#22C55E15;display:flex;align-items:center;justify-content:center;font-size:20px;border:1px solid #22C55E30">⚡</div>
                        <div>
                            <div style="font-size:15px;font-weight:700">Action Builder</div>
                            <div style="font-size:12px;color:var(--saas-text-muted)">Define actions with rules & effects</div>
                        </div>
                    </div>
                    <p style="font-size:12px;color:var(--saas-text-secondary);line-height:1.5">Configure actions with parameters, pre-condition rules, side effects (webhooks, notifications), and undo support.</p>
                </div>

                <!-- Function Editor Card -->
                <div class="voyant-card" style="padding:24px;cursor:pointer;transition:all 0.2s"
                    @click=${() => this._openFunctionEditor()}>
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                        <div style="width:44px;height:44px;border-radius:10px;background:#8B5CF615;display:flex;align-items:center;justify-content:center;font-size:20px;border:1px solid #8B5CF630">💻</div>
                        <div>
                            <div style="font-size:15px;font-weight:700">Function Editor</div>
                            <div style="font-size:12px;color:var(--saas-text-muted)">Python / TypeScript with Monaco</div>
                        </div>
                    </div>
                    <p style="font-size:12px;color:var(--saas-text-secondary);line-height:1.5">Write and test sandboxed functions with Monaco editor. Supports Python and TypeScript with syntax highlighting.</p>
                </div>
            </div>

            ${this._renderFilterBuilder()}
        </div>`;
    }

    render() {
        const totalInstances = this.types.reduce((s, t) => s + (t.instance_count || 0), 0);

        return html`
        <saas-sidebar currentPath="/admin/ontology"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)" role="main" aria-label="Ontology explorer">
            <!-- Header -->
            <div style="padding:32px 32px 0;display:flex;align-items:center;justify-content:space-between">
                <div>
                    <h1 style="font-size:28px;font-weight:900;font-family:Geist,Inter,system-ui,sans-serif;letter-spacing:-0.02em;color:var(--saas-text-primary)">Ontology Explorer</h1>
                    <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">${this.types.length} object types · ${this.links.length} link types · ${totalInstances.toLocaleString()} instances</p>
                </div>
                <div style="display:flex;gap:8px;align-items:center">
                    <button class="voyant-btn-primary voyant-btn" style="font-size:13px;padding:8px 16px" aria-label="Create new object type" @click=${this._openTypeBuilder}>
                        ➕ Create Type
                    </button>
                    <div class="voyant-tabs" role="tablist" aria-label="Ontology view mode">
                        <button class="voyant-tab ${this.view === 'table' ? 'active' : ''}" role="tab" aria-selected=${this.view === 'table'} @click=${() => { this.view = 'table'; }}>📋 Table</button>
                        <button class="voyant-tab ${this.view === 'grid' ? 'active' : ''}" role="tab" aria-selected=${this.view === 'grid'} @click=${() => { this.view = 'grid'; }}>⊞ Grid</button>
                        <button class="voyant-tab ${this.view === 'graph' ? 'active' : ''}" role="tab" aria-selected=${this.view === 'graph'} @click=${() => { this.view = 'graph'; }}>🕸️ Graph</button>
                        <button class="voyant-tab ${this.view === 'builders' ? 'active' : ''}" role="tab" aria-selected=${this.view === 'builders'} @click=${() => { this.view = 'builders'; }}>🔧 Builders</button>
                    </div>
                </div>
            </div>

            <!-- Metrics Bar -->
            ${this._renderMetrics()}

            <!-- Search Bar -->
            ${this._renderSearchBar()}

            <!-- Filter Builder Toggle (table/grid/graph views) -->
            ${this.view !== 'builders' ? html`
            <div style="padding:0 32px 12px">
                <button class="voyant-btn ${this.filterBuilderOpen ? 'active' : ''}" style="font-size:11px;padding:5px 12px"
                    aria-expanded=${this.filterBuilderOpen}
                    aria-controls="filter-builder-panel"
                    @click=${() => { this.filterBuilderOpen = !this.filterBuilderOpen; }}>
                    🔍 ${this.filterBuilderOpen ? 'Hide' : 'Show'} Filter Builder
                    ${this.filterConditions.length > 0 ? html`<span style="margin-left:4px;padding:1px 6px;border-radius:10px;background:var(--saas-brand);color:white;font-size:10px">${this.filterConditions.length}</span>` : ''}
                </button>
            </div>
            ${this.filterBuilderOpen ? this._renderFilterBuilder() : ''}
            ` : ''}

            ${this.loading ? html`<div style="text-align:center;padding:80px;color:var(--saas-text-muted)" role="status" aria-live="polite">Loading ontology...</div>` : html`

            <!-- Table View -->
            ${this.view === 'table' ? this._renderTableView() : ''}

            <!-- Grid View -->
            ${this.view === 'grid' ? this._renderGridView() : ''}

            <!-- Graph View -->
            ${this.view === 'graph' ? html`
            <div style="padding:0 32px 32px">
                <div class="voyant-card" style="overflow:hidden">
                    <div style="width:100%;height:520px">
                        <voyant-graph-view
                            .nodes=${this._graphNodes()}
                            .edges=${this._graphEdges()}
                            @node-click=${this._onNodeClick}
                        ></voyant-graph-view>
                    </div>
                </div>
            </div>` : ''}

            <!-- Builders View -->
            ${this.view === 'builders' ? this._renderBuildersView() : ''}

            `}

            <!-- Detail Panel -->
            <voyant-detail-panel
                .open=${this.detailOpen}
                .title=${this.detailTarget?.kind === 'type' ? this.detailTarget.data.name : this.detailTarget?.kind === 'instance' ? `Object Instance` : ''}
                .subtitle=${this.detailTarget?.kind === 'type' ? `Object Type · v${this.detailTarget.data.version}` : this.detailTarget?.kind === 'instance' ? `${this.detailTarget.data.object_type_name || this.detailTarget.data.object_type} · v${this.detailTarget.data.version}` : ''}
                @close=${() => this._closeDetail()}
            >
                ${this._renderDetailContent()}
            </voyant-detail-panel>

            <!-- Builder Modals -->
            ${this._renderTypeBuilderModal()}
            ${this._renderActionBuilderModal()}
            ${this._renderFunctionEditorModal()}
            ${this._renderEditInstanceModal()}
        </main>`;
    }
}
