import React from 'react';
import { Bell, Settings, User } from 'lucide-react';
import logoImage from '../assets/LOGO.jpg';

export default function Header({ activeTabLabel }) {
    return (
        <header className="bg-[#0B0F19]/85 backdrop-blur-xl border-b border-slate-800/60 h-16 flex items-center justify-between px-6 shrink-0 sticky top-0 z-40 shadow-lg w-full transition-all duration-300">

            {/* Left: Logo and Static Project Title */}
            <div className="flex items-center space-x-5">

                <div className="flex items-center space-x-3 pr-5 border-r border-slate-800/60">
                    <div className="relative">
                        {/* Subtle glow behind the logo */}
                        <div className="absolute inset-0 bg-indigo-500/30 blur-md rounded-full"></div>
                        <img
                            src={logoImage}
                            alt="PipeVision Logo"
                            className="w-9 h-9 rounded-xl shadow-sm object-cover bg-white relative z-10 border border-slate-800"
                            onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.nextSibling.style.display = 'flex';
                            }}
                        />
                        <div className="hidden w-9 h-9 rounded-xl bg-indigo-600 items-center justify-center font-bold shadow-sm text-white relative z-10">
                            🔵
                        </div>
                    </div>
                    {/* Aesthetic text gradient for the title */}
                    <h1 className="text-xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-400">
                        PipeTally
                    </h1>
                </div>

                {/* Dynamic Page Title */}
                <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-400 hidden sm:block bg-indigo-950/40 px-3 py-1 rounded-lg border border-indigo-500/20">
                    {activeTabLabel}
                </h2>
            </div>

            {/* Right: Aesthetic Utilities */}
            <div className="flex items-center space-x-3 text-slate-400">
                <button className="p-2 hover:bg-slate-800/60 hover:text-indigo-400 rounded-xl transition-all duration-200">
                    <Bell className="w-5 h-5" />
                </button>
                <button className="p-2 hover:bg-slate-800/60 hover:text-indigo-400 rounded-xl transition-all duration-200">
                    <Settings className="w-5 h-5" />
                </button>
                <div className="w-9 h-9 bg-gradient-to-tr from-indigo-600 to-cyan-500 text-white rounded-xl flex items-center justify-center font-bold shadow-md shadow-indigo-500/20 ml-2 cursor-pointer hover:scale-105 transition-transform duration-200">
                    <User className="w-4 h-4" />
                </div>
            </div>

        </header>
    );
}