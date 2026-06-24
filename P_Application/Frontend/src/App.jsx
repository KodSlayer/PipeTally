import React, { useState } from 'react';
import { AlertCircle } from 'lucide-react';

// Components
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import UploadDropzone from './components/UploadDropzone';
import MetricCard from './components/MetricCard';
import EmptyState from './components/EmptyState';
import ImageCropper from './components/ImageCropper';

// Logic & Data
import { detectStackedPipes, detectSinglePipes } from './services/api';
import { calculateAccuracyPercentage } from './utils/calculations';
import referenceData from './assets/stacked_pipe_counts.json';

export default function App() {
    const [detectionMode, setDetectionMode] = useState('stacked'); // 'single' or 'stacked'
    const [viewMode, setViewMode] = useState('standard'); // 'standard', 'crop', or 'compare'
    const [selectedFile, setSelectedFile] = useState(null);
    const [previewUrl, setPreviewUrl] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [results, setResults] = useState(null);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    // Compute dynamic label for Header and layout title
    const getActiveTabLabel = () => {
        if (viewMode === 'crop') return 'Crop Region';
        if (viewMode === 'compare') return 'Side-by-Side Comparison';
        return detectionMode === 'single' ? 'Single Pipe Detection' : 'Stacked Pipe Detection';
    };

    // Unified lookup function for reference counts
    const getReferenceCount = (filename) => {
        if (!referenceData || !referenceData.images || !filename) return null;
        const match = referenceData.images.find(img => img.image_name === filename);
        return match ? match.exact_pipe_count : null;
    };

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setSelectedFile(file);
            setPreviewUrl(URL.createObjectURL(file));
            setResults(null);
            setError(null);
        }
    };

    const handleDetection = async () => {
        if (!selectedFile) return;
        setLoading(true);
        setError(null);

        try {
            let data;
            if (detectionMode === 'single') {
                data = await detectSinglePipes(selectedFile);
            } else {
                data = await detectStackedPipes(selectedFile);
            }
            setResults(data);
        } catch (err) {
            setError(err.message || "An unexpected error occurred.");
        } finally {
            setLoading(false);
        }
    };

    const handleCropSave = (croppedBlob) => {
        const croppedFile = new File([croppedBlob], `cropped_${selectedFile.name}`, { type: 'image/jpeg' });
        setSelectedFile(croppedFile);
        setPreviewUrl(URL.createObjectURL(croppedBlob));
        setViewMode('standard');
        setResults(null);
        setError(null);
    };

    const exactCount = selectedFile ? getReferenceCount(selectedFile.name) : null;
    const hasReference = exactCount !== null;
    const showSegments = detectionMode === 'stacked';

    // Calculate number of columns dynamically for horizontal layout
    let cardCount = 2; // Detected and Model are always shown
    if (hasReference) cardCount += 2; // Reference and Accuracy
    if (showSegments) cardCount += 1; // Segments

    const gridClass = 
        cardCount === 5 ? 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5' :
        cardCount === 4 ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4' :
        cardCount === 3 ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2';

    return (
        <div className="flex flex-col h-screen bg-[#080B11] font-sans text-slate-100 overflow-hidden">
            <Header activeTabLabel={getActiveTabLabel()} />

            <div className="flex flex-1 overflow-hidden relative">
                <Sidebar
                    detectionMode={detectionMode}
                    setDetectionMode={setDetectionMode}
                    viewMode={viewMode}
                    setViewMode={setViewMode}
                    isOpen={isSidebarOpen}
                    toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                />

                <main className="flex-1 overflow-y-auto p-6 lg:p-10 transition-all duration-300">
                    <div className="max-w-6xl mx-auto">
                        <header className="mb-8">
                            <h2 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-400">
                                {getActiveTabLabel()}
                            </h2>
                        </header>

                        {viewMode === 'crop' && previewUrl ? (
                            <ImageCropper
                                imageSrc={previewUrl}
                                onCropSave={handleCropSave}
                                onCancel={() => setViewMode('standard')}
                            />
                        ) : (
                            <>
                                <UploadDropzone
                                    onFileChange={handleFileChange}
                                    onDetect={handleDetection}
                                    selectedFile={selectedFile}
                                    previewUrl={previewUrl}
                                    loading={loading}
                                    onClear={() => { setSelectedFile(null); setPreviewUrl(null); setResults(null); }}
                                />

                                {error && (
                                    <div className="mb-8 p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start text-rose-200">
                                        <AlertCircle className="w-5 h-5 mr-3 mt-0.5 text-rose-400" />
                                        <p className="text-sm font-medium">{error}</p>
                                    </div>
                                )}

                                {previewUrl && (
                                    <>
                                        {/* Linear Metrics Cards Displayed Below the Upload Section */}
                                        <div className={`grid gap-4 mb-8 ${gridClass}`}>
                                            <MetricCard 
                                                label="Detected Pipes" 
                                                value={results ? (results.pipe_count ?? 0) : (loading ? "..." : "--")} 
                                                accent="#6366F1" 
                                            />
                                            
                                            {hasReference && (
                                                <>
                                                    <MetricCard 
                                                        label="Reference Count" 
                                                        value={exactCount} 
                                                        accent="#64748B" 
                                                    />
                                                    <MetricCard 
                                                        label="Accuracy" 
                                                        value={results ? (calculateAccuracyPercentage(results.pipe_count, exactCount) !== null
                                                            ? `${calculateAccuracyPercentage(results.pipe_count, exactCount)}%`
                                                            : "N/A") : "--"} 
                                                        accent="#10B981" 
                                                    />
                                                </>
                                            )}

                                            {showSegments && (
                                                <MetricCard 
                                                    label="Segments" 
                                                    value={results ? (results.segments ?? 0) : (loading ? "..." : "--")} 
                                                    accent="#EC4899" 
                                                />
                                            )}

                                            <MetricCard 
                                                label="Detection Model" 
                                                value={results?.model || (loading ? "Analyzing..." : (detectionMode === 'single' ? "Mask R-CNN" : "Mask R-CNN + YOLO (Hybrid)"))} 
                                                accent="#06B6D4" 
                                            />
                                        </div>

                                        {/* Image Display Section */}
                                        {viewMode === 'compare' ? (
                                            /* Side-by-Side Comparison Layout */
                                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                                {/* Left Column: Original Upload */}
                                                <div className="bg-slate-900/40 border border-slate-800/80 p-5 rounded-2xl shadow-xl flex flex-col">
                                                    <div className="flex justify-between items-center mb-3">
                                                        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Original Image</span>
                                                        <span className="text-[10px] bg-slate-805 text-slate-350 px-2 py-0.5 rounded-full font-mono border border-slate-700/60">
                                                            Original
                                                        </span>
                                                    </div>
                                                    <div className="bg-slate-950/60 rounded-xl overflow-hidden border border-slate-800/60 flex items-center justify-center flex-1 min-h-[300px]">
                                                        <img src={previewUrl} alt="Original Upload" className="max-h-[450px] object-contain w-full" />
                                                    </div>
                                                </div>

                                                {/* Right Column: Processed Result */}
                                                <div className="bg-slate-900/40 border border-slate-800/80 p-5 rounded-2xl shadow-xl flex flex-col">
                                                    <div className="flex justify-between items-center mb-3">
                                                        <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Detection Output</span>
                                                        {results && (
                                                            <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-mono">
                                                                ID: #{results.detection_id ?? 'N/A'}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="bg-slate-950/60 rounded-xl overflow-hidden border border-slate-800/60 flex items-center justify-center flex-1 min-h-[300px] relative">
                                                        {results?.image_base64 ? (
                                                            <img src={`data:image/jpeg;base64,${results.image_base64}`} alt="Processed Result" className="max-h-[450px] object-contain w-full" />
                                                        ) : (
                                                            <div className="text-center p-8 text-slate-500 flex flex-col items-center justify-center">
                                                                {loading ? (
                                                                    <>
                                                                        <span className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500/30 border-t-indigo-500 mb-3"></span>
                                                                        <span className="text-sm">Processing image via API...</span>
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-3 text-slate-650 font-bold">
                                                                            AI
                                                                        </div>
                                                                        <span className="text-sm">Click "Run Detection" above to generate output</span>
                                                                    </>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ) : (
                                            /* Single View Layout (Standard View) */
                                            <div className="bg-slate-900/40 border border-slate-800/80 p-5 rounded-2xl shadow-xl flex flex-col max-w-4xl mx-auto">
                                                <div className="flex justify-between items-center mb-3">
                                                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                                                        {results ? "Processed Detection Output" : "Image Preview"}
                                                    </span>
                                                    {results && (
                                                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-mono">
                                                            ID: #{results.detection_id ?? 'N/A'}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="bg-slate-950/60 rounded-xl overflow-hidden border border-slate-800/60 flex items-center justify-center min-h-[350px]">
                                                    <img 
                                                        src={results?.image_base64 ? `data:image/jpeg;base64,${results.image_base64}` : previewUrl} 
                                                        alt="Active View" 
                                                        className="max-h-[500px] object-contain w-full" 
                                                    />
                                                </div>
                                            </div>
                                        )}
                                    </>
                                )}

                                {!previewUrl && <EmptyState />}
                            </>
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
}