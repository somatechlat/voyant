import React from 'react';
import { MarketplaceCard } from './components/MarketplaceCard';
import { BidList } from './components/BidList';
import { Wallet, Bell, Search, Menu } from 'lucide-react';

function App() {
    return (
        <div className="min-h-screen bg-slate-50 pb-20">

            {/* Header */}
            <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center">
                            <span className="text-xl font-display font-bold text-slate-900 tracking-tight">Voyant<span className="text-blue-500">.</span></span>
                        </div>

                        <div className="flex-1 max-w-lg mx-8 hidden md:block">
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Search size={16} className="text-slate-400" />
                                </div>
                                <input
                                    type="text"
                                    className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg leading-5 bg-slate-50 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-all"
                                    placeholder="Search data requests..."
                                />
                            </div>
                        </div>

                        <div className="flex items-center space-x-6">
                            <div className="flex items-end flex-col hidden sm:flex">
                                <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">Balance</span>
                                <span className="text-sm font-bold text-slate-900 font-display">$1,248.50</span>
                            </div>
                            <button className="p-2 rounded-full text-slate-400 hover:text-slate-500 hover:bg-slate-100 transition-colors relative">
                                <Bell size={20} />
                                <span className="absolute top-2 right-2 block h-2 w-2 rounded-full bg-red-500 ring-2 ring-white"></span>
                            </button>
                            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-600"></div>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">

                {/* Hero Section */}
                <div className="mb-10">
                    <h1 className="text-3xl font-display font-bold text-slate-900 mb-2">Data Marketplace</h1>
                    <p className="text-slate-500 max-w-2xl">
                        Control your digital footprint. Earn from your data on your terms.
                        <span className="text-slate-900 font-medium"> Live requests pay 3x premium.</span>
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                    {/* Left Column: Data Cards */}
                    <div className="lg:col-span-2 space-y-6">
                        <div className="flex items-center justify-between mb-2">
                            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Active Requests</h2>
                        </div>

                        <div className="space-y-4">
                            {/* LIVE CARD EXAMPLE */}
                            <MarketplaceCard
                                type="location"
                                title="Exact Location Stream"
                                description="Live GPS coordinates for high-density event crowd analysis. Requires 15 mins of active sharing."
                                price={4.50}
                                trustScore={98}
                                isLive={true}
                                anonymizationLevel="Partial"
                            />

                            {/* HISTORICAL CARD EXAMPLE */}
                            <MarketplaceCard
                                type="photos"
                                title="Camera Roll Meta"
                                description="Metadata from last 30 days of photos (EXIF only, no images). Market research study."
                                price={9.00}
                                trustScore={94}
                                isLive={false}
                                anonymizationLevel="Full"
                            />

                            <MarketplaceCard
                                type="messages"
                                title="Message Sentiment"
                                description="NLP sentiment analysis of SMS history. Text content is processed locally and never leaves device."
                                price={13.25}
                                trustScore={99}
                                isLive={false}
                                anonymizationLevel="Full"
                            />
                        </div>
                    </div>

                    {/* Right Column: Bids & Wallet */}
                    <div className="space-y-6">
                        <BidList />

                        <div className="glass-card p-6 bg-gradient-to-br from-slate-900 to-slate-800 text-white border-transparent">
                            <h3 className="text-sm font-medium text-slate-300 mb-1">Total Lifetime Earnings</h3>
                            <div className="flex items-baseline space-x-1 mb-6">
                                <span className="text-3xl font-bold font-display">$8,432.12</span>
                                <span className="text-sm text-emerald-400 font-medium">+12% this month</span>
                            </div>
                            <button className="w-full py-3 bg-white text-slate-900 rounded-lg font-bold text-sm hover:bg-slate-50 transition-colors">
                                Cash Out
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

export default App;
