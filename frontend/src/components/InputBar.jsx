import React from 'react';

export default function InputBar({
  input,
  onInput,
  onSubmit,
  onKeyDown,
  textareaRef,
  isPaused,
  loading,
  isOnline
}) {
  return (
    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#0a0a0a] via-[#0a0a0a] to-transparent pt-6 pb-6 px-4">
      <div className="max-w-3xl mx-auto">
        <form
          onSubmit={onSubmit}
          style={{ outline: 'none', boxShadow: 'none' }}
          className="bg-[#2f2f2f] rounded-[24px] flex items-end p-2 transition-colors"
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={onInput}
            onKeyDown={onKeyDown}
            disabled={isPaused || loading || !isOnline}
            aria-label="Message prompt input"
            placeholder={
              !isOnline
                ? 'Waking up the server — this can take up to a minute…'
                : (isPaused ? 'Approve or reject above...' : 'Ask anything')
            }
            rows={1}
            style={{ outline: 'none', boxShadow: 'none', border: 'none', WebkitTapHighlightColor: 'transparent' }}
            className="flex-1 max-h-[200px] bg-transparent resize-none py-2.5 px-4 text-[15px] text-gray-100 placeholder-gray-400 disabled:opacity-50 focus:outline-none focus:ring-0 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={isPaused || loading || !input.trim() || !isOnline}
            aria-label="Send message"
            className="p-2 mb-1 mr-1 bg-white hover:bg-gray-200 disabled:bg-[#424242] disabled:text-gray-500 text-black rounded-full transition-colors flex-shrink-0 cursor-pointer disabled:cursor-not-allowed"
          >
            <svg 
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg" 
              width="18" 
              height="18" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2.5" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            >
              <line x1="12" y1="19" x2="12" y2="5"></line>
              <polyline points="5 12 12 5 19 12"></polyline>
            </svg>
          </button>
        </form>
        <div className="text-center mt-3 text-[11px] text-gray-500">
          Logistics SLA Copilot can make mistakes. Check important generated data.
        </div>
      </div>
    </div>
  );
}
