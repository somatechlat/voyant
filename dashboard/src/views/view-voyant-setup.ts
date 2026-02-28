import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import '../components/saas-layout';
import '../components/saas-glass-modal';
import '../components/saas-infra-card';

@customElement('view-voyant-setup')
export class ViewVoyantSetup extends LitElement {
    @state() modalOpen = false;
    @state() modalTitle = '';

    createRenderRoot() { return this; }

    openModal(title: string) {
        this.modalTitle = title;
        this.modalOpen = true;
    }

    closeModal() {
        this.modalOpen = false;
    }

    render() {
        return html`
      <saas-layout>
        <!-- Header -->
        <header class="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-100 h-16 flex items-center justify-between px-8">
          <span class="font-semibold text-lg">Voyant Data Platform</span>
          <div class="flex items-center gap-2">
            <div class="h-2 w-2 rounded-full bg-saas-success animate-pulse"></div>
            <span class="text-sm font-medium">Data Engineer</span>
          </div>
        </header>

        <!-- Dashboard Grid (Voyant Specific Layout) -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 p-8 h-[calc(100vh-64px-80px)] overflow-y-auto">
          
          <!-- Col 1: Platform Infra -->
          <div class="space-y-6">
            <h2 class="text-2xl font-bold tracking-tight">Data Pipeline</h2>
            <div class="grid gap-4">
              <saas-infra-card name="Scraper Engine (Selenium/Playwright)" status="connected" @edit="${() => this.openModal('Configure Scraper')}"></saas-infra-card>
              <saas-infra-card name="Data Lake (S3)" status="connected" @edit="${() => this.openModal('Configure S3 Lake')}"></saas-infra-card>
              <saas-infra-card name="Vector Store (Pinecone)" status="pending" @edit="${() => this.openModal('Configure Vector DB')}"></saas-infra-card>
            </div>
          </div>

          <!-- Col 2: Customers/Projects -->
          <div class="space-y-6">
            <div class="flex items-center justify-between">
              <h2 class="text-2xl font-bold tracking-tight">Data Projects</h2>
              <button @click="${() => this.openModal('New Project')}" class="rounded-lg bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">
                + New Project
              </button>
            </div>
            
            <div class="grid gap-4">
              <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
                 <div class="flex items-center justify-between">
                   <div class="flex items-center gap-4">
                     <div class="h-10 w-10 rounded-lg bg-black text-white flex items-center justify-center font-bold">M</div>
                     <div>
                       <h3 class="font-semibold">Market Analysis Alpha</h3>
                       <p class="text-xs text-gray-500">1.2M Records • Daily Sync</p>
                     </div>
                   </div>
                   <span class="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700">Syncing</span>
                 </div>
              </div>
            </div>
          </div>

        </div>

        <!-- Footer / Launch Bar -->
        <div class="fixed bottom-0 left-0 right-0 h-20 bg-white border-t border-gray-100 flex items-center justify-center px-8 z-40">
           <button class="w-full max-w-4xl rounded-xl bg-black h-12 text-white font-bold uppercase tracking-widest hover:bg-gray-900 transition-colors shadow-lg">
             Deploy Pipeline
           </button>
        </div>

        <!-- Glass Modal -->
        <saas-glass-modal ?open="${this.modalOpen}" title="${this.modalTitle}" @close="${this.closeModal}">
          <div class="space-y-4">
             <div>
               <p class="text-sm text-gray-600 mb-4">Configure source nodes for this pipeline component.</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Configuration JSON</label>
              <textarea class="w-full h-32 rounded-lg border border-gray-200 px-4 py-2 focus:border-black focus:ring-black font-mono text-sm" placeholder="{ 'max_threads': 4 }"></textarea>
            </div>
            <div class="pt-4 flex justify-end gap-3">
              <button @click="${this.closeModal}" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-black">Cancel</button>
              <button @click="${this.closeModal}" class="px-6 py-2 rounded-lg bg-black text-sm font-medium text-white hover:bg-gray-900">Update Config</button>
            </div>
          </div>
        </saas-glass-modal>

      </saas-layout>
    `;
    }
}
