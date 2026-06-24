const API_BASE = "http://localhost:8006";

export const detectStackedPipes = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE}/detect/stacked`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            let detail = await response.text();
            try {
                const json = JSON.parse(detail);
                detail = json.detail || detail;
            } catch (e) {
                // Keep raw text if not JSON
            }
            throw new Error(`API error ${response.status}: ${detail}`);
        }

        return await response.json();
    } catch (err) {
        if (err.message.includes('Failed to fetch')) {
            throw new Error("Cannot connect to API. Make sure the FastAPI server is running on port 8006.");
        }
        throw err;
    }
};

export const detectSinglePipes = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE}/detect/single`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            let detail = await response.text();
            try {
                const json = JSON.parse(detail);
                detail = json.detail || detail;
            } catch (e) {
                // Keep raw text if not JSON
            }
            throw new Error(`API error ${response.status}: ${detail}`);
        }

        return await response.json();
    } catch (err) {
        if (err.message.includes('Failed to fetch')) {
            throw new Error("Cannot connect to API. Make sure the FastAPI server is running on port 8006.");
        }
        throw err;
    }
};