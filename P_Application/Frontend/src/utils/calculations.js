export const calculateAccuracyPercentage = (predictedCount, exactCount) => {
    if (exactCount < 0) return null;
    if (exactCount === 0) return predictedCount === 0 ? 100.0 : 0.0;

    const diff = Math.abs(exactCount - predictedCount);
    const accuracy = Math.max(0, 100 - (diff / exactCount) * 100);
    return accuracy.toFixed(2);
};