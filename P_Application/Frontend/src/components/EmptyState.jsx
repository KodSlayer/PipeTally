import React from 'react';
import { Image as ImageIcon } from 'lucide-react';

export default function EmptyState() {
    return (
        <div className="bg-slate-900/20 border border-slate-800/60 rounded-2xl p-12 text-center flex flex-col items-center shadow-lg backdrop-blur-sm">
            <div className="w-16 h-16 bg-slate-950/80 text-indigo-400 border border-slate-800/80 rounded-2xl flex items-center justify-center mb-4 shadow-[0_0_15px_rgba(79,70,229,0.15)]">
                <ImageIcon className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">No Image Loaded</h3>
            <p className="text-slate-400 max-w-md text-sm">
                Upload a pipe image using the uploader above to begin detection.
            </p>
        </div>
    );
}