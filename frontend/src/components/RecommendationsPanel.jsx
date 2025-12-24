import React from "react";

export default function RecommendationsPanel({ items }) {
    if (!items || items.length === 0) return null;

    return (
        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">Top 12 Growth Picks (USA + Canada)</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {items.map((item, i) => (
                    <div key={i} className="border rounded-md p-3">
                        <div className="flex justify-between items-center">
                            <div className="font-semibold text-gray-900">{item.ticker}</div>
                            <div className="text-xs text-gray-500">{item.market}</div>
                        </div>
                        <div className="text-sm text-gray-700">{item.name}</div>
                        <div className="text-xs text-gray-600 mt-2">{item.rationale}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
