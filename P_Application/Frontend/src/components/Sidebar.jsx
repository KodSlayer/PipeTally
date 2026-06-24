import React from 'react';
import { Server, Check, Menu, ChevronLeft } from 'lucide-react';

export default function Sidebar({ 
    detectionMode, 
    setDetectionMode, 
    viewMode, 
    setViewMode, 
    isOpen, 
    toggleSidebar 
}) {
    return (
        <aside
            className={`${isOpen ? 'w-72' : 'w-20'} bg-[#0B0F19] border-r border-slate-800/60 text-slate-350 flex flex-col shadow-2xl z-30 transition-all duration-300 ease-in-out shrink-0 relative`}
        >
            {/* Top Bar for the Collapse Toggle */}
            <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/60 shrink-0">
                {isOpen && (
                    <span className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400 tracking-widest text-xs uppercase ml-2">
                        Control Panel
                    </span>
                )}
                <button
                    onClick={toggleSidebar}
                    className={`p-2 rounded-xl bg-slate-800/40 hover:bg-slate-700/60 text-slate-350 transition-all duration-200 active:scale-95 border border-slate-700/50 ${!isOpen && 'mx-auto'}`}
                >
                    {isOpen ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
            </div>

            {/* Checklist-style Navigation Menu */}
            <div className="flex-1 py-6 space-y-6 overflow-y-auto overflow-x-hidden">
                
                {/* Section 1: Detection Target */}
                <div>
                    {isOpen ? (
                        <span className="font-bold text-slate-500 tracking-wider text-[10px] uppercase px-6 block mb-3">
                            Detection Target
                        </span>
                    ) : (
                        <div className="w-full border-b border-slate-800/40 mb-3 pb-1 text-center">
                            <span className="text-[9px] text-slate-500 font-bold uppercase">Target</span>
                        </div>
                    )}
                    <div className="space-y-1.5 px-3">
                        <button
                            onClick={() => setDetectionMode('single')}
                            title={!isOpen ? "Single Pipe Detection" : ""}
                            className={`w-full flex items-center p-3 rounded-xl transition-all duration-200 group ${
                                detectionMode === 'single'
                                    ? 'bg-slate-800/40 text-white'
                                    : 'text-slate-400 hover:bg-slate-800/25 hover:text-slate-200'
                            }`}
                        >
                            <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all shrink-0 ${
                                detectionMode === 'single'
                                    ? 'bg-gradient-to-tr from-indigo-600 to-cyan-500 border-indigo-500 text-white shadow-[0_0_10px_rgba(79,70,229,0.3)] font-bold'
                                    : 'border-slate-750 bg-slate-950/40 text-transparent hover:border-slate-650'
                            }`}>
                                <Check className="w-3.5 h-3.5 stroke-[3.5]" />
                            </div>
                            {isOpen && <span className="text-sm font-semibold ml-3.5 whitespace-nowrap">Single Pipes</span>}
                        </button>

                        <button
                            onClick={() => setDetectionMode('stacked')}
                            title={!isOpen ? "Stacked Pipe Detection" : ""}
                            className={`w-full flex items-center p-3 rounded-xl transition-all duration-200 group ${
                                detectionMode === 'stacked'
                                    ? 'bg-slate-800/40 text-white'
                                    : 'text-slate-400 hover:bg-slate-800/25 hover:text-slate-200'
                            }`}
                        >
                            <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all shrink-0 ${
                                detectionMode === 'stacked'
                                    ? 'bg-gradient-to-tr from-indigo-600 to-cyan-500 border-indigo-500 text-white shadow-[0_0_10px_rgba(79,70,229,0.3)] font-bold'
                                    : 'border-slate-750 bg-slate-950/40 text-transparent hover:border-slate-655'
                            }`}>
                                <Check className="w-3.5 h-3.5 stroke-[3.5]" />
                            </div>
                            {isOpen && <span className="text-sm font-semibold ml-3.5 whitespace-nowrap">Stacked Pipes</span>}
                        </button>
                    </div>
                </div>

                {/* Section 2: Analysis Layout */}
                <div>
                    {isOpen ? (
                        <span className="font-bold text-slate-500 tracking-wider text-[10px] uppercase px-6 block mb-3">
                            Analysis View
                        </span>
                    ) : (
                        <div className="w-full border-b border-slate-800/40 mb-3 pb-1 text-center">
                            <span className="text-[9px] text-slate-500 font-bold uppercase">View</span>
                        </div>
                    )}
                    <div className="space-y-1.5 px-3">
                        <button
                            onClick={() => setViewMode('standard')}
                            title={!isOpen ? "Standard View" : ""}
                            className={`w-full flex items-center p-3 rounded-xl transition-all duration-200 group ${
                                viewMode === 'standard'
                                    ? 'bg-slate-800/40 text-white'
                                    : 'text-slate-400 hover:bg-slate-800/25 hover:text-slate-200'
                            }`}
                        >
                            <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all shrink-0 ${
                                viewMode === 'standard'
                                    ? 'bg-gradient-to-tr from-indigo-600 to-cyan-500 border-indigo-500 text-white shadow-[0_0_10px_rgba(79,70,229,0.3)] font-bold'
                                    : 'border-slate-750 bg-slate-950/40 text-transparent hover:border-slate-655'
                            }`}>
                                <Check className="w-3.5 h-3.5 stroke-[3.5]" />
                            </div>
                            {isOpen && <span className="text-sm font-semibold ml-3.5 whitespace-nowrap">Standard View</span>}
                        </button>

                        <button
                            onClick={() => setViewMode('compare')}
                            title={!isOpen ? "Side-by-Side Compare" : ""}
                            className={`w-full flex items-center p-3 rounded-xl transition-all duration-200 group ${
                                viewMode === 'compare'
                                    ? 'bg-slate-800/40 text-white'
                                    : 'text-slate-400 hover:bg-slate-800/25 hover:text-slate-200'
                            }`}
                        >
                            <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all shrink-0 ${
                                viewMode === 'compare'
                                    ? 'bg-gradient-to-tr from-indigo-600 to-cyan-500 border-indigo-500 text-white shadow-[0_0_10px_rgba(79,70,229,0.3)] font-bold'
                                    : 'border-slate-750 bg-slate-950/40 text-transparent hover:border-slate-655'
                            }`}>
                                <Check className="w-3.5 h-3.5 stroke-[3.5]" />
                            </div>
                            {isOpen && <span className="text-sm font-semibold ml-3.5 whitespace-nowrap">Side-by-Side Compare</span>}
                        </button>

                        <button
                            onClick={() => setViewMode('crop')}
                            title={!isOpen ? "Crop Region" : ""}
                            className={`w-full flex items-center p-3 rounded-xl transition-all duration-200 group ${
                                viewMode === 'crop'
                                    ? 'bg-slate-800/40 text-white'
                                    : 'text-slate-400 hover:bg-slate-800/25 hover:text-slate-200'
                            }`}
                        >
                            <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all shrink-0 ${
                                viewMode === 'crop'
                                    ? 'bg-gradient-to-tr from-indigo-600 to-cyan-500 border-indigo-500 text-white shadow-[0_0_10px_rgba(79,70,229,0.3)] font-bold'
                                    : 'border-slate-750 bg-slate-950/40 text-transparent hover:border-slate-655'
                            }`}>
                                <Check className="w-3.5 h-3.5 stroke-[3.5]" />
                            </div>
                            {isOpen && <span className="text-sm font-semibold ml-3.5 whitespace-nowrap">Crop Region</span>}
                        </button>
                    </div>
                </div>

            </div>

            {/* API Status Footer */}
            <div className={`p-4 border-t border-slate-800/60 transition-all duration-300 ${isOpen ? 'opacity-100' : 'opacity-0 hidden'}`}>
                <div className="bg-slate-900/80 p-3.5 rounded-xl border border-slate-800 shadow-inner">
                    <div className="flex items-center text-xs text-slate-500 mb-2 font-bold uppercase tracking-wider">
                        <Server className="w-3.5 h-3.5 mr-2" />
                        System Status
                    </div>
                    <div className="flex items-center space-x-2 text-xs font-medium bg-emerald-500/10 text-emerald-400 py-1.5 px-3 rounded-lg border border-emerald-500/20 w-max">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                        <span>API Online</span>
                    </div>
                </div>
            </div>
        </aside>
    );
}