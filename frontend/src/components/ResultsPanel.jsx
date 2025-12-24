import React from "react";

export default function ResultsPanel({ result }) {
    if (!result) return null;

    const { ticker, price_data, analysis, evidence_pack, score, disclaimer } = result;

    return (
        <div className="bg-white p-6 rounded-lg shadow-lg border-t-4 border-indigo-500 animate-fade-in">
            <div className="flex justify-between items-start mb-6 border-b pb-4">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">{ticker} <span className="text-gray-500 text-lg font-normal">analysis</span></h2>
                    <p className="text-sm text-gray-500">{new Date().toLocaleString()}</p>
                </div>
                <div className="text-right">
                    <div className="text-3xl font-bold text-gray-900">
                        {typeof price_data?.current_price === "number" ? `$${price_data.current_price.toFixed(2)}` : "N/A"}
                    </div>
                    <div className={`text-sm font-medium ${price_data?.change_1d_pct >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {typeof price_data?.change_1d_pct === "number" ? `${price_data.change_1d_pct.toFixed(2)}% (1D)` : "1D change N/A"}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="md:col-span-2 space-y-6">
                    {analysis?.executive_summary && (
                        <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
                            <h3 className="font-bold text-indigo-800 mb-2">Executive Summary</h3>
                            <p className="text-sm text-indigo-900">{analysis.executive_summary}</p>
                            {analysis?.expected_return && (
                                <p className="text-sm text-indigo-900 mt-2">
                                    Expected return: {analysis.expected_return}
                                </p>
                            )}
                        </div>
                    )}
                    {!analysis?.executive_summary && analysis?.expected_return && (
                        <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
                            <h3 className="font-bold text-indigo-800 mb-2">Expected Return</h3>
                            <p className="text-sm text-indigo-900">{analysis.expected_return}</p>
                        </div>
                    )}
                    <Section title="News Summary" items={analysis?.news_summary} color="indigo" />
                    <Section title="Bull Case" items={analysis?.bull_case} color="green" />
                    <Section title="Bear Case" items={analysis?.bear_case} color="red" />
                    <Section title="Key Risks" items={analysis?.key_risks} color="orange" />
                    {analysis?.last_quarter_result && (
                        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                            <h3 className="font-bold text-gray-700 mb-2">Last Quarter Result</h3>
                            <p className="text-sm text-gray-700">{analysis.last_quarter_result}</p>
                        </div>
                    )}
                </div>

                <div className="space-y-6">
                    <div className="bg-gray-50 p-4 rounded-lg">
                        <h3 className="font-bold text-gray-700 mb-2">FinSight Score</h3>
                        <div className="text-4xl font-black text-indigo-600">
                            {typeof score?.total === "number" ? score.total.toFixed(2) : score?.total}/100
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{score?.notes}</p>
                        {Array.isArray(score?.breakdown) && score.breakdown.length > 0 && (
                            <div className="mt-3 text-xs text-gray-600">
                                {score.breakdown.map((item, i) => (
                                    <div key={i} className="flex justify-between">
                                        <span>{item.label}</span>
                                        <span>{item.value > 0 ? `+${item.value}` : item.value}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="bg-blue-50 p-4 rounded-lg">
                        <h3 className="font-bold text-blue-800 mb-2">Evidence Pack</h3>
                        <ul className="text-xs space-y-2 text-blue-900">
                            {evidence_pack?.map((ev, i) => (
                                <li key={i} className="border-b border-blue-100 pb-1 last:border-0">
                                    <span className="font-semibold block">{ev.date} {ev.source ? `- ${ev.source}` : ""}</span>
                                    {ev.title && <span className="block">{ev.title}</span>}
                                    {ev.claim}
                                    {ev.url && (
                                        <a className="block font-semibold text-blue-700 underline" href={ev.url} target="_blank" rel="noreferrer">
                                            Source
                                        </a>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            </div>

            <div className="text-xs text-gray-400 border-t pt-4 text-center">
                {disclaimer || "Not financial advice."}
            </div>
        </div>
    );
}

function Section({ title, items, color }) {
    if (!items || items.length === 0) return null;
    const list = Array.isArray(items) ? items : [items];
    const colorClass = {
        indigo: "text-indigo-700",
        green: "text-green-700",
        red: "text-red-700",
        orange: "text-orange-700"
    }[color] || "text-gray-700";
    const parseSource = (text) => {
        const match = text.match(/\(source:\s*(https?:\/\/\S+)\)/i);
        if (!match) return { text, url: "" };
        const url = match[1].replace(/\).*$/, "");
        const cleaned = text.replace(match[0], "").trim();
        return { text: cleaned, url };
    };

    return (
        <div>
            <h3 className={`font-bold text-lg mb-2 ${colorClass}`}>{title}</h3>
            <ul className="list-disc pl-5 space-y-1 text-gray-700">
                {list.map((item, i) => {
                    const parsed = parseSource(String(item));
                    return (
                        <li key={i}>
                            <span>{parsed.text}</span>
                            {parsed.url && (
                                <a
                                    className="ml-2 font-semibold text-blue-700 underline"
                                    href={parsed.url}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    Source
                                </a>
                            )}
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
