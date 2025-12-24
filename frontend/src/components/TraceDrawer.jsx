import React, { useState } from 'react';

export default function TraceDrawer({ result }) {
    const [isOpen, setIsOpen] = useState(false);

    if (!result || !result.validation) return null;

    return (
        <div className="fixed bottom-0 left-0 right-0 bg-gray-900 text-white shadow-xl opacity-95">
            <div
                className="p-2 flex justify-between items-center cursor-pointer border-t border-gray-700 hover:bg-gray-800"
                onClick={() => setIsOpen(!isOpen)}
            >
                <span className="font-mono text-sm ml-4">
                    🔍 Debug Trace | Validation: <span className={result.validation.status === "PASS" ? "text-green-400" : "text-red-400"}>{result.validation.status}</span>
                </span>
                <span className="mr-4">{isOpen ? "▼" : "▲"}</span>
            </div>

            {isOpen && (
                <div className="p-4 overflow-auto max-h-64 font-mono text-xs text-gray-300">
                    <p>Validation Reasons: {JSON.stringify(result.validation.reasons)}</p>
                    <p>Suggested Route: {result.validation.suggested_route}</p>
                    {/* Add dummy trace details if available */}
                    <pre className="mt-2 text-gray-500 whitespace-pre-wrap">
                        {JSON.stringify(result, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
}
