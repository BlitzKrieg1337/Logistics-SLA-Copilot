import React from 'react';

const SUGGESTIONS = [
  "Check for recent order delays",
  "Analyze MSA with Siemens",
  "Calculate late delivery penalties",
  "Verify contract terms for Tata"
];

export default function SuggestionGrid({ onSelectSuggestion, isOnline }) {
  return (
    <div className="h-full flex flex-col items-center justify-center max-w-4xl mx-auto w-full px-4">
      <h1 
        className="text-2xl md:text-3xl font-medium text-gray-100 mb-8 tracking-tight text-center" 
        style={{ fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace' }}
      >
        📋 Logistics SLA Copilot active. How can I help you analyze contracts,<br /> verify compliance, or track SLA metrics today?
      </h1>
      
      {/* Suggestion Cards */}
      <section 
        aria-label="Suggested prompts" 
        className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl mt-4"
      >
        {SUGGESTIONS.map((text, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSelectSuggestion(text)}
            disabled={!isOnline}
            aria-label={`Prompt suggestion: ${text}`}
            className="text-left p-4 rounded-xl border border-white/10 bg-[#1a1a1a]/60 hover:bg-[#2f2f2f] transition-all hover:border-white/20 disabled:opacity-50 disabled:cursor-not-allowed group flex justify-between items-center shadow-sm"
          >
            <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
              {text}
            </span>
            <svg 
              aria-hidden="true"
              className="w-4 h-4 text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity transform group-hover:translate-x-1" 
              viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            >
              <line x1="5" y1="12" x2="19" y2="12"></line>
              <polyline points="12 5 19 12 12 19"></polyline>
            </svg>
          </button>
        ))}
      </section>
    </div>
  );
}
