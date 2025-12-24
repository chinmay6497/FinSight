import React, { useState } from 'react';

export default function QuestionCard({ onAnalyze, disabled }) {
    const [question, setQuestion] = useState("");

    const handleSubmit = (e) => {
        e.preventDefault();
        if (question.trim()) {
            onAnalyze(question);
        }
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">2. Ask FinSight</h2>
            <form onSubmit={handleSubmit} className="flex gap-4">
                <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="e.g., Should I invest in AAPL now?"
                    className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                    disabled={disabled}
                />
                <button
                    type="submit"
                    disabled={disabled || !question.trim()}
                    className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {disabled ? "Analyzing..." : "Analyze"}
                </button>
            </form>
            {disabled && <p className="text-sm text-gray-500 mt-2">Agent is researching... this may take 10-20 seconds.</p>}
        </div>
    );
}
