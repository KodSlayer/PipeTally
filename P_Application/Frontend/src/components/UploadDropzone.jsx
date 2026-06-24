import React from 'react';
import { Upload, X } from 'lucide-react';

export default function UploadDropzone({ onFileChange, onDetect, selectedFile, previewUrl, loading, onClear }) {
    return (
        <div className="bg-slate-900/40 border border-slate-800/80 p-6 rounded-2xl shadow-xl backdrop-blur-md mb-8">
            {!selectedFile ? (
                <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-slate-800/60 border-dashed rounded-xl cursor-pointer bg-slate-950/40 hover:bg-slate-950/60 hover:border-indigo-500/40 text-slate-400 hover:text-slate-200 transition-all duration-300">
                    <Upload className="w-10 h-10 text-slate-500 mb-3 group-hover:text-indigo-400 transition-colors" />
                    <p className="text-sm font-medium">Click or drop image to upload</p>
                    <p className="text-xs text-slate-600 mt-1">Supports PNG, JPG, JPEG</p>
                    <input type="file" className="hidden" accept="image/*" onChange={onFileChange} />
                </label>
            ) : (
                <div className="flex flex-col items-center">
                    <div className="relative w-full h-64 bg-slate-950/60 rounded-xl overflow-hidden mb-4 border border-slate-800/60 flex items-center justify-center">
                        <img src={previewUrl} alt="Preview" className="w-full h-full object-contain" />
                        <button 
                            onClick={onClear} 
                            className="absolute top-3 right-3 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/30 p-1.5 rounded-xl transition-all duration-200 hover:scale-105"
                            title="Remove image"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                    <button
                        onClick={onDetect}
                        disabled={loading}
                        className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-bold rounded-xl shadow-[0_4px_20px_rgba(79,70,229,0.25)] hover:shadow-[0_4px_25px_rgba(79,70,229,0.4)] disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 disabled:shadow-none transition-all duration-300 active:scale-95 flex items-center justify-center space-x-2"
                    >
                        {loading ? (
                            <>
                                <span className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></span>
                                <span>Analyzing...</span>
                            </>
                        ) : (
                            <span>Run Detection</span>
                        )}
                    </button>
                </div>
            )}
        </div>
    );
}