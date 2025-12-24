import React, { useState } from 'react';
import { api } from './api';
import ProfileCard from './components/ProfileCard';
import QuestionCard from './components/QuestionCard';
import ResultsPanel from './components/ResultsPanel';
import TraceDrawer from './components/TraceDrawer';
import RecommendationsPanel from './components/RecommendationsPanel';

function App() {
  const [profile, setProfile] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSaveProfile = async (p) => {
    try {
      const saved = await api.saveProfile(p);
      setProfile(saved);
      const recos = await api.recommendations(p);
      setRecommendations(recos?.items || []);
      alert("Stock picks updated!");
    } catch (e) {
      alert("Failed to save profile: " + e.message);
    }
  };

  const handleAnalyze = async (question) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      if (!profile) throw new Error("Please save profile first.");
      const res = await api.analyze(question, profile);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 relative pb-20">
      <header className="bg-indigo-900 text-white p-6 shadow-md">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-3xl font-bold tracking-tight">FinSight</h1>
          <p className="text-indigo-200">Financial News Analyst Agent (Demo)</p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-4 md:p-8 space-y-6">
        <ProfileCard onSave={handleSaveProfile} />
        <RecommendationsPanel items={recommendations} />

        {profile ? (
          <QuestionCard onAnalyze={handleAnalyze} disabled={loading} />
        ) : (
          <div className="bg-yellow-50 text-yellow-800 p-4 rounded border border-yellow-200">
            ⚠ Please save your budget and risk profile to unlock analysis.
          </div>
        )}

        {loading && (
          <div className="text-center py-12 animate-pulse">
            <div className="inline-block w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-4"></div>
            <p className="text-indigo-800 font-medium">Analyzing market data & news...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-800 p-4 rounded border border-red-200">
            Error: {error}
          </div>
        )}

        <ResultsPanel result={result} />
      </main>

      <TraceDrawer result={result} />

      <footer className="text-center text-xs text-gray-500 py-6">
        Made with &lt;3 by Chinmay Raval from Canada · ravalchinmay6497@gmail.com
      </footer>
    </div>
  );
}

export default App;
