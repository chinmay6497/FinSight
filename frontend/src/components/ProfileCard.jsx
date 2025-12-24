import React, { useState } from 'react';

export default function ProfileCard({ onSave }) {
    const [budget, setBudget] = useState(5000);
    const [risk, setRisk] = useState("medium");
    const [horizon, setHorizon] = useState("6m");

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave({ budget: Number(budget), risk, horizon });
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">1. Your Profile</h2>
            <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                <div>
                    <label className="block text-sm font-medium text-gray-700">Budget ($)</label>
                    <input
                        type="number"
                        value={budget}
                        onChange={(e) => setBudget(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                        required
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700">Risk Level</label>
                    <select
                        value={risk}
                        onChange={(e) => setRisk(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                    >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700">Horizon</label>
                    <select
                        value={horizon}
                        onChange={(e) => setHorizon(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                    >
                        <option value="1m">1 Month</option>
                        <option value="6m">6 Months</option>
                        <option value="1y">1 Year</option>
                    </select>
                </div>
                <button
                    type="submit"
                    className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                    Get Stock Picks
                </button>
            </form>
        </div>
    );
}
