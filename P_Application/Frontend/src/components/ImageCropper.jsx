import React, { useState, useRef } from 'react';
import ReactCrop, { centerCrop, makeAspectCrop } from 'react-image-crop';
import { Crop, Check, RefreshCw } from 'lucide-react';
import 'react-image-crop/dist/ReactCrop.css';

// Helper to center the initial crop outline
function centerAspectCrop(mediaWidth, mediaHeight, aspect) {
    return centerCrop(
        makeAspectCrop({ unit: '%', width: 90 }, aspect, mediaWidth, mediaHeight),
        mediaWidth,
        mediaHeight
    );
}

export default function ImageCropper({ imageSrc, onCropSave, onCancel }) {
    const [crop, setCrop] = useState();
    const [completedCrop, setCompletedCrop] = useState(null);
    const imgRef = useRef(null);

    function onImageLoad(e) {
        const { width, height } = e.currentTarget;
        // Leaving aspect unconstrained so the user can crop any rectangle shape
        setCrop(centerAspectCrop(width, height, undefined));
    }

    // Generates the cropped image blob from the canvas coordinates
    async function getCroppedImgBlob(image, cropObj) {
        const canvas = document.createElement('canvas');
        const scaleX = image.naturalWidth / image.width;
        const scaleY = image.naturalHeight / image.height;

        canvas.width = cropObj.width;
        canvas.height = cropObj.height;
        const ctx = canvas.getContext('2d');

        if (!ctx) return null;

        ctx.drawImage(
            image,
            cropObj.x * scaleX,
            cropObj.y * scaleY,
            cropObj.width * scaleX,
            cropObj.height * scaleY,
            0,
            0,
            cropObj.width,
            cropObj.height
        );

        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                if (!blob) return resolve(null);
                resolve(blob);
            }, 'image/jpeg');
        });
    }

    async function handleConfirmCrop() {
        if (imgRef.current && completedCrop?.width && completedCrop?.height) {
            const croppedBlob = await getCroppedImgBlob(imgRef.current, completedCrop);
            if (croppedBlob) {
                // Pass the cropped file blob back up to your parent handler
                onCropSave(croppedBlob);
            }
        }
    }

    return (
        <div className="bg-slate-900/40 border border-slate-800/80 p-6 rounded-2xl shadow-xl backdrop-blur-md flex flex-col items-center">
            <div className="w-full flex justify-between items-center mb-4 border-b border-slate-800/80 pb-3">
                <div className="flex items-center space-x-2">
                    <Crop className="w-5 h-5 text-indigo-400" />
                    <h4 className="font-semibold text-white">Crop Image Region</h4>
                </div>
                <p className="text-xs text-slate-400">Drag corners to focus on specific pipes</p>
            </div>

            <div className="max-w-full max-h-[500px] overflow-auto border border-slate-800/80 rounded-xl bg-slate-950/60 flex items-center justify-center p-2">
                <ReactCrop
                    crop={crop}
                    onChange={(c) => setCrop(c)}
                    onComplete={(c) => setCompletedCrop(c)}
                >
                    <img
                        ref={imgRef}
                        alt="Crop Source"
                        src={imageSrc}
                        onLoad={onImageLoad}
                        className="max-w-full max-h-[460px] object-contain"
                    />
                </ReactCrop>
            </div>

            <div className="flex justify-end space-x-3 w-full mt-6">
                <button
                    onClick={onCancel}
                    className="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-850 hover:bg-slate-800 rounded-xl border border-slate-700/40 transition-colors"
                >
                    Cancel
                </button>
                <button
                    onClick={handleConfirmCrop}
                    disabled={!completedCrop?.width}
                    className={`flex items-center space-x-2 px-5 py-2 text-sm font-bold text-white rounded-xl shadow-md transition-all ${!completedCrop?.width
                            ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-800'
                            : 'bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 active:scale-95'
                        }`}
                >
                    <Check className="w-4 h-4" />
                    <span>Apply Selection</span>
                </button>
            </div>
        </div>
    );
}