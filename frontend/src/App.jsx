import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const STATUS_CONFIG = {
  checking: { dot: 'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.5)]', text: 'Connecting…' },
  waking:   { dot: 'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.5)] animate-pulse', text: 'Waking up server…' },
  online:   { dot: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]', text: 'Connected' },
  offline:  { dot: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]', text: 'Offline' },
};

export default function App() {
  const [threadId, setThreadId] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isPaused, setIsPaused] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('checking');

  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Initialize Session
  useEffect(() => {
    let currentThread = sessionStorage.getItem('thread_id');
    if (!currentThread) {
      currentThread = uuidv4();
      sessionStorage.setItem('thread_id', currentThread);
    }
    setThreadId(currentThread);
    fetchHistory(currentThread);
  }, []);

  // Connection polling — fast while not confirmed online (to catch Render
  // cold-start wake-ups quickly), slower once steady-state connected.
  useEffect(() => {
    let cancelled = false;
    let failCount = 0;
    let timeoutId;

    const checkConnection = async () => {
      try {
        await axios.get(`${API_BASE}/test`, { timeout: 8000 });
        if (cancelled) return;
        
        failCount = 0;
        setConnectionStatus('online');
        // SUCCESS: We stop polling entirely. No more timeouts!
        // This allows Render to sleep after 15 mins of inactivity.
        
      } catch (error) {
        if (cancelled) return;
        
        failCount += 1;
        setConnectionStatus(failCount >= 6 ? 'offline' : 'waking');
        
        // FAILURE: Keep polling every 5 seconds until it wakes up
        timeoutId = setTimeout(checkConnection, 5000);
      }
    };

    checkConnection();
    
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, []);

  // Delete thread data when the tab closes
  useEffect(() => {
    const cleanup = () => {
      if (!threadId) return;
      navigator.sendBeacon(`${API_BASE}/thread/${threadId}/delete`);
    };

    window.addEventListener('pagehide', cleanup);
    return () => window.removeEventListener('pagehide', cleanup);
  }, [threadId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isPaused, loading]);

  const SUGGESTIONS = [
    "Check for recent order delays",
    "Analyze MSA with Siemens",
    "Calculate late delivery penalties",
    "Verify contract terms for Tata"
  ];

  const handleSuggestionClick = (text) => {
    setInput(text);
    if (textareaRef.current) {
      textareaRef.current.focus();
      // Reset height to fit the new text
      textareaRef.current.style.height = 'auto';
    }
  };

  const fetchHistory = async (id) => {
    try {
      const res = await axios.get(`${API_BASE}/history/${id}`);
      if (res.data.messages) setMessages(res.data.messages);
      setIsPaused(res.data.is_paused || false);
      setPendingAction(res.data.pending_action || null);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  const handleInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  const sendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || isPaused || loading || connectionStatus !== 'online') return;

    const userMessage = input;
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const res = await axios.post(
        `${API_BASE}/chat`,
        { thread_id: threadId, messages: userMessage },
        { timeout: 65000 } // headroom for a Render cold-start on the backend
      );
      setMessages(res.data.messages || []);
      setIsPaused(res.data.is_paused || false);
      setPendingAction(res.data.pending_action || null);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Connection error. Please check if FastAPI is running.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleApproval = async (action) => {
    setLoading(true);
    try {
      const res = await axios.post(
        `${API_BASE}/action`,
        {
          thread_id: threadId,
          action: action,
          reason: action === 'reject' ? 'User rejected execution' : null
        },
        { timeout: 65000 }
      );
      setMessages(res.data.messages || []);
      setIsPaused(res.data.is_paused || false);
      setPendingAction(res.data.pending_action || null);
    } catch (error) {
      console.error('Action error:', error);
    } finally {
      setLoading(false);
    }
  };

  const isOnline = connectionStatus === 'online';

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-gray-100 font-sans selection:bg-blue-500/30 overflow-hidden relative">

      {/* Floating Status Capsule */}
      <div className="absolute top-5 left-5 z-50">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#171717]/80 backdrop-blur-md rounded-full border border-white/5 shadow-md">
          <div className={`w-2 h-2 rounded-full ${STATUS_CONFIG[connectionStatus].dot}`} />
          <span className="text-xs font-medium text-gray-300">
            {STATUS_CONFIG[connectionStatus].text}
          </span>
        </div>
      </div>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col relative min-w-0">
        <div className="flex-1 overflow-y-auto px-4 pt-20 pb-32">
          {messages.length === 0 && !isPaused && !loading ? (
            <div className="h-full flex flex-col items-center justify-center max-w-4xl mx-auto w-full px-4">
              <h1 className="text-2xl md:text-3xl font-medium text-gray-100 mb-8 tracking-tight text-center font-serif" style={{ fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace' }}>
                📋 Logistics SLA Copilot active. How can I help you analyze contracts,<br /> verify compliance, or track SLA metrics today?
              </h1>
              
              {/* Suggestion Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl mt-4">
                {SUGGESTIONS.map((text, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestionClick(text)}
                    disabled={!isOnline}
                    className="text-left p-4 rounded-xl border border-white/10 bg-[#1a1a1a]/60 hover:bg-[#2f2f2f] transition-all hover:border-white/20 disabled:opacity-50 disabled:cursor-not-allowed group flex justify-between items-center shadow-sm"
                  >
                    <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
                      {text}
                    </span>
                    <svg 
                      className="w-4 h-4 text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity transform group-hover:translate-x-1" 
                      viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    >
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                      <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6 mt-6">
              {messages.filter((m) => m.role !== 'tool' && m.role !== 'system').map((msg, idx) => {
                const isUser = msg.role === 'user' || msg.role === 'human';
                return (
                  <div key={idx} className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
                    <div className={`text-[15px] leading-relaxed max-w-[85%] md:max-w-[75%] ${
                      isUser
                        ? 'bg-[#2f2f2f] text-white px-5 py-3 rounded-3xl'
                        : 'text-gray-200 px-2 py-3'
                    }`}>
                      {isUser ? (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      ) : (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            table: ({node, ...props}) => (
                              <div className="overflow-x-auto my-4 border border-white/10 rounded-lg">
                                <table className="w-full text-sm text-left border-collapse" {...props} />
                              </div>
                            ),
                            th: ({node, ...props}) => <th className="bg-[#1a1a1a] px-4 py-3 font-medium text-gray-300 border-b border-white/10" {...props} />,
                            td: ({node, ...props}) => <td className="px-4 py-3 border-b border-white/5 last:border-0" {...props} />,
                            p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                            strong: ({node, ...props}) => <strong className="font-semibold text-white" {...props} />,
                            ul: ({node, ...props}) => <ul className="list-disc list-inside mb-4 space-y-1" {...props} />,
                            ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-4 space-y-1" {...props} />,
                            a: ({node, ...props}) => <a className="text-blue-400 hover:text-blue-300 underline underline-offset-2" target="_blank" rel="noopener noreferrer" {...props} />
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      )}
                    </div>
                  </div>
                );
              })}

              {loading && (
                <div className="flex justify-start px-2 py-3">
                  <div className="flex gap-1.5 items-center">
                    <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}

              {/* Approval UI */}
              {isPaused && pendingAction && (
                <div className="my-6 border border-gray-700 bg-[#1a1a1a] rounded-2xl p-5 md:p-6 shadow-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-2 w-2 rounded-full bg-orange-500 animate-pulse" />
                    <h3 className="text-gray-100 font-medium text-sm">Action Approval Required</h3>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-3">
                    <button
                      onClick={() => handleApproval('approve')}
                      disabled={loading}
                      className="flex-1 py-2.5 px-4 bg-white text-black hover:bg-gray-200 font-medium rounded-full text-sm transition disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleApproval('reject')}
                      disabled={loading}
                      className="flex-1 py-2.5 px-4 bg-[#2f2f2f] text-white hover:bg-gray-700 font-medium rounded-full text-sm transition disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} className="h-4" />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#0a0a0a] via-[#0a0a0a] to-transparent pt-6 pb-6 px-4">
          <div className="max-w-3xl mx-auto">
            <form
              onSubmit={sendMessage}
              style={{ outline: 'none', boxShadow: 'none' }}
              className="bg-[#2f2f2f] rounded-[24px] flex items-end p-2 transition-colors"
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInput}
                onKeyDown={handleKeyDown}
                disabled={isPaused || loading || !isOnline}
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
                className="p-2 mb-1 mr-1 bg-white hover:bg-gray-200 disabled:bg-[#424242] disabled:text-gray-500 text-black rounded-full transition-colors flex-shrink-0"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
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
      </main>
    </div>
  );
}