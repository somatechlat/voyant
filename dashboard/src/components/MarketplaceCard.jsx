import React from 'react';
import { MapPin, Image, MessageSquare, Music, Shield, Info, Activity } from 'lucide-react';
import { clsx } from 'clsx';

const ICONS = {
    location: MapPin,
    photos: Image,
    messages: MessageSquare,
    music: Music,
};

export function MarketplaceCard({
    type,
    title,
    description,
    points,
    price,
    isLive = false,
    anonymizationLevel = 'Full',
    trustScore = 98
}) {
    const Icon = ICONS[type] || Activity;

    return (
        <div className={clsx(
            "glass-card p-6 transition-all duration-300 hover:shadow-md relative overflow-hidden group",
            isLive ? "border-l-4 border-l-red-500" : "border-l-4 border-l-transparent"
        )}>
            {/* Live Indicator overlay */}
            {isLive && (
                <div className="absolute top-4 right-4 flex items-center space-x-2 bg-red-50 px-2 py-1 rounded-full border border-red-100">
                    <span className="live-indicator">
                        <span className="live-indicator-ping"></span>
                        <span className="live-indicator-dot"></span>
                    </span>
                    <span className="text-xs font-bold text-red-600 tracking-wide uppercase">LIVE REQUEST</span>
                </div>
            )}

            <div className="flex items-start justify-between mb-6">
                <div className="flex items-center space-x-4">
                    <div className="p-3 bg-slate-100 rounded-xl text-slate-600 group-hover:bg-slate-200 transition-colors">
                        <Icon size={24} strokeWidth={1.5} />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-slate-900 leading-tight">{title}</h3>
                        <p className="text-sm text-slate-500 mt-1">{description}</p>
                    </div>
                </div>
            </div>

            {/* Main Data Points Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-1">Anonymization</p>
                    <div className="flex items-center space-x-2">
                        <Shield size={14} className="text-emerald-500" />
                        <span className="text-sm font-semibold text-slate-700">{anonymizationLevel}</span>
                    </div>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-1">Trust Score</p>
                    <div className="flex items-center space-x-2">
                        <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                            <div className="h-full bg-slate-800 rounded-full" style={{ width: `${trustScore}%` }}></div>
                        </div>
                        <span className="text-xs font-bold text-slate-700">{trustScore}%</span>
                    </div>
                </div>
            </div>

            {/* Footer / Action */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                <div className="flex flex-col">
                    <span className="text-xs text-slate-400 font-medium uppercase">Est. Earnings</span>
                    <span className="text-xl font-display font-bold text-slate-900">${price.toFixed(2)}</span>
                </div>

                <button className={clsx(
                    "px-5 py-2.5 rounded-lg text-sm font-semibold transition-all transform active:scale-95",
                    isLive
                        ? "bg-red-500 text-white hover:bg-red-600 shadow-lg shadow-red-200"
                        : "bg-slate-900 text-white hover:bg-slate-800"
                )}>
                    {isLive ? "Share Live Data" : "Sell History"}
                </button>
            </div>
        </div>
    );
}
