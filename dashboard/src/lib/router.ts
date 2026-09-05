/**
 * Simple router for Lit 3 — no external dependency.
 */

import { html, render, type TemplateResult } from 'lit';

type RouteHandler = () => TemplateResult;

interface Route {
    pattern: RegExp;
    handler: RouteHandler;
}

class SimpleRouter {
    private routes: Route[] = [];
    private outlet: HTMLElement;

    constructor(outlet: HTMLElement) {
        this.outlet = outlet;
        window.addEventListener('popstate', () => this.resolve());
    }

    setRoutes(routes: Array<{ path: string; component?: RouteHandler; render?: RouteHandler }>) {
        this.routes = routes.map(r => {
            const pattern = r.path.replace(/:(\w+)/g, '([^/]+)');
            return {
                pattern: new RegExp(`^${pattern}$`),
                handler: r.component || r.render || (() => html``),
            };
        });
        this.resolve();
    }

    navigate(path: string) {
        window.history.pushState({}, '', path);
        this.resolve();
    }

    resolve() {
        const path = window.location.pathname;
        for (const route of this.routes) {
            if (route.pattern.test(path)) {
                render(route.handler(), this.outlet);
                return;
            }
        }
        // Fallback to /
        for (const route of this.routes) {
            if (route.pattern.test('/')) {
                render(route.handler(), this.outlet);
                return;
            }
        }
    }
}

export { SimpleRouter as Router };
