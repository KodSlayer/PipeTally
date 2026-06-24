import React from 'react';

export default function MetricCard({ label, value, accent = "#4F46E5" }) {
    const isLongValue = typeof value === 'string' && value.length > 15;
    const valueSizeClass = isLongValue 
        ? "text-sm sm:text-base font-bold text-white tracking-normal leading-tight break-words" 
        : "text-3xl font-extrabold text-white tracking-tight";

    return (
        <div 
            className="bg-slate-900/60 backdrop-blur-md rounded-xl p-5 flex flex-col justify-center border border-slate-800/60 shadow-lg transition-all duration-300 hover:scale-[1.02] hover:border-slate-700/80 min-h-[110px]"
            style={{ 
                boxShadow: `0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.05), inset 0 1px 1px rgba(255, 255, 255, 0.05), 0 0 12px ${accent}15`
            }}
        >
            <div className="flex items-center space-x-2.5 mb-2">
                <div className="w-2.5 h-2.5 rounded-full animate-pulse shrink-0" style={{ backgroundColor: accent, boxShadow: `0 0 8px ${accent}` }}></div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest truncate">{label}</span>
            </div>
            <div className={valueSizeClass}>
                {value}
            </div>
        </div>
    );
}