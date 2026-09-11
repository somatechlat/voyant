/**
 * Voyant Keyboard Shortcuts — Global keyboard shortcut system.
 *
 * Registers global shortcuts and displays a help overlay (? key).
 * All shortcuts are documented and user-discoverable.
 */

export interface Shortcut {
    key: string;
    modifiers?: ('meta' | 'ctrl' | 'shift' | 'alt')[];
    description: string;
    action: () => void;
    category?: string;
}

const _shortcuts: Shortcut[] = [];
let _helpVisible = false;
let _helpToggle: (() => void) | null = null;

/** Register a keyboard shortcut. */
export function registerShortcut(shortcut: Shortcut) {
    _shortcuts.push(shortcut);
}

/** Get all registered shortcuts (for help overlay). */
export function getShortcuts(): Shortcut[] {
    return [..._shortcuts];
}

/** Initialize the global keyboard handler. Call once at app init. */
export function initKeyboard() {
    document.addEventListener('keydown', (e: KeyboardEvent) => {
        // Don't fire shortcuts when typing in inputs
        const target = e.target as HTMLElement;
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
            // Only allow Cmd+K and Escape in inputs
            if (!((e.metaKey || e.ctrlKey) && e.key === 'k') && e.key !== 'Escape') {
                return;
            }
        }

        for (const shortcut of _shortcuts) {
            const mods = shortcut.modifiers || [];
            const metaMatch = mods.includes('meta') ? e.metaKey : !e.metaKey;
            const ctrlMatch = mods.includes('ctrl') ? e.ctrlKey : !e.ctrlKey;
            const shiftMatch = mods.includes('shift') ? e.shiftKey : !e.shiftKey;
            const altMatch = mods.includes('alt') ? e.altKey : !e.altKey;

            if (e.key === shortcut.key && metaMatch && ctrlMatch && shiftMatch && altMatch) {
                e.preventDefault();
                shortcut.action();
                return;
            }
        }
    });
}

/** Default shortcuts for the Voyant dashboard. */
export function registerDefaultShortcuts() {
    registerShortcut({
        key: 'k',
        modifiers: ['meta'],
        description: 'Open command palette',
        category: 'Navigation',
        action: () => {
            // Triggered by the command palette component itself
        },
    });

    registerShortcut({
        key: '?',
        description: 'Show keyboard shortcuts',
        category: 'Help',
        action: () => {
            _helpToggle?.();
        },
    });

    registerShortcut({
        key: 'Escape',
        description: 'Close modal / panel',
        category: 'Navigation',
        action: () => {
            // Dispatched to close any open modal/panel
            document.dispatchEvent(new CustomEvent('voyant:escape'));
        },
    });

    registerShortcut({
        key: '1',
        modifiers: ['meta'],
        description: 'Go to Dashboard',
        category: 'Navigation',
        action: () => { window.location.href = '/admin'; },
    });

    registerShortcut({
        key: '2',
        modifiers: ['meta'],
        description: 'Go to Ontology',
        category: 'Navigation',
        action: () => { window.location.href = '/admin/ontology'; },
    });

    registerShortcut({
        key: '3',
        modifiers: ['meta'],
        description: 'Go to SQL Console',
        category: 'Navigation',
        action: () => { window.location.href = '/admin/sql'; },
    });

    registerShortcut({
        key: '4',
        modifiers: ['meta'],
        description: 'Go to Scraper',
        category: 'Navigation',
        action: () => { window.location.href = '/admin/scraper'; },
    });

    registerShortcut({
        key: '5',
        modifiers: ['meta'],
        description: 'Go to Agents',
        category: 'Navigation',
        action: () => { window.location.href = '/admin/agents'; },
    });
}
