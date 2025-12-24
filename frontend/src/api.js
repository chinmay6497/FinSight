const API_BASE = "http://localhost:8000";

export const api = {
    health: async () => {
        const res = await fetch(`${API_BASE}/health`);
        return res.json();
    },

    saveProfile: async (profile) => {
        const res = await fetch(`${API_BASE}/profile`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(profile),
        });
        return res.json();
    },
    recommendations: async (profile) => {
        const res = await fetch(`${API_BASE}/recommendations`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(profile),
        });
        return res.json();
    },

    analyze: async (question, profile) => {
        const res = await fetch(`${API_BASE}/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, profile }),
        });
        if (!res.ok) throw new Error("Analysis failed");
        return res.json();
    }
};
