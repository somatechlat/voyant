/**
 * Simple event bus for cross-filtering between dashboard components.
 * Implements FR-5.4.2.3 (Cross-filtering) from VOYANT_MIMO_MERGE_SPEC.
 *
 * Events:
 *   filter:apply  — a component has applied a filter (detail: { field, value, source })
 *   filter:clear  — all filters should be cleared (detail: { field?, source? })
 *   drilldown     — user wants to drill into a data point (detail: { field, value, source })
 *
 * Usage:
 *   import { eventBus } from './event-bus';
 *   eventBus.on('filter:apply', (data) => { ... });
 *   eventBus.emit('filter:apply', { field: 'status', value: 'running', source: 'chart' });
 */

export type FilterEvent = {
    field: string;
    value: unknown;
    source: string; // component that originated the event
};

export type DrilldownEvent = {
    field: string;
    value: unknown;
    source: string;
    row?: Record<string, unknown>;
};

export type VoyantEventMap = {
    'filter:apply': FilterEvent;
    'filter:clear': Partial<FilterEvent>;
    'drilldown': DrilldownEvent;
};

export type VoyantEventType = keyof VoyantEventMap;

type Callback<T = unknown> = (data: T) => void;

class EventBus {
    private _listeners = new Map<string, Set<Callback>>();

    /**
     * Subscribe to an event.
     * Returns an unsubscribe function for convenience.
     */
    on<K extends VoyantEventType>(event: K, callback: Callback<VoyantEventMap[K]>): () => void {
        if (!this._listeners.has(event)) {
            this._listeners.set(event, new Set());
        }
        this._listeners.get(event)!.add(callback as Callback);
        return () => this.off(event, callback);
    }

    /**
     * Unsubscribe from an event.
     */
    off<K extends VoyantEventType>(event: K, callback: Callback<VoyantEventMap[K]>): void {
        this._listeners.get(event)?.delete(callback as Callback);
    }

    /**
     * Emit an event to all listeners.
     */
    emit<K extends VoyantEventType>(event: K, data: VoyantEventMap[K]): void {
        this._listeners.get(event)?.forEach(cb => {
            try {
                cb(data);
            } catch (err) {
                console.error(`[event-bus] Error in listener for "${event}":`, err);
            }
        });
    }

    /**
     * Remove all listeners (useful for testing).
     */
    clear(): void {
        this._listeners.clear();
    }
}

/** Singleton instance shared across the dashboard. */
export const eventBus = new EventBus();
