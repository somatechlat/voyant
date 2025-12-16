import React, { useEffect, useState } from 'react';
import { ArrowUpRight, Clock } from 'lucide-react';

export function BidList() {
    const [bids, setBids] = useState([
        { id: 1, type: 'location', source: 'Market Research Corp', amount: 12.40, time: '2m ago', isLive: false },
        { id: 2, type: 'device', source: 'GameAnalytics Ltd', amount: 4.50, time: 'Just now', isLive: true },
        { id: 3, type: 'shopping', source: 'RetailMetric Inc', amount: 8.20, time: '5m ago', isLive: false },
    ]);

    return (
        <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-2">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Real-time Activity</h2>
                </div>
                <button className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center">
                    View All <ArrowUpRight size={12} className="ml-1" />
                </button>
            </div>

            <div className="space-y-4">
                {bids.map((bid) => (
                    <div key={bid.id} className="group flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer border border-transparent hover:border-slate-100">
                        <div className="flex items-center space-x-3">
                            <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-600">
                                {bid.source[0]}
                            </div>
                            <div>
                                <div className="flex items-center space-x-2">
                                    <p className="text-sm font-semibold text-slate-900">{bid.source}</p>
                                    {bid.isLive && (
                                        <span className="text-[10px] font-bold px-1.5 py-0.5 bg-red-100 text-red-600 rounded-full border border-red-200 uppercase tracking-wide">
                                            LIVE
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs text-slate-500 mt-0.5 flex items-center">
                                    <Clock size={10} className="mr-1" /> {bid.time}
                                </p>
                            </div>
                        </div>
                        <div className="text-right">
                            <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">
                                +${bid.amount.toFixed(2)}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
