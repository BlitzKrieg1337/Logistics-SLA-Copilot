import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import axios from 'axios';

import StatusCapsule from './components/StatusCapsule';
import SuggestionGrid from './components/SuggestionGrid';
import ChatMessage from './components/ChatMessage';
import ApprovalCard from './components/ApprovalCard';
import InputBar from './components/InputBar';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

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
  const activeAbortController = useRef(null);

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
        // Stop polling once connected to allow Render free-tier to sleep when inactive
      } catch (error) {
        if (cancelled) return;
        
        failCount += 1;
        setConnectionStatus(failCount >= 6 ? 'offline' : 'waking');
        
        // Retry every 5 seconds until connected
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

  const handleSuggestionClick = (text) => {
    setInput(text);
    if (textareaRef.current) {
      textareaRef.current.focus();
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

    const userMessage = input.trim();
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    // Cancel any previous in-flight request
    if (activeAbortController.current) {
      activeAbortController.current.abort();
    }
    const controller = new AbortController();
    activeAbortController.current = controller;

    try {
      const res = await axios.post(
        `${API_BASE}/chat`,
        { 
          thread_id: threadId, 
          message: userMessage,
          messages: userMessage // backwards compatibility
        },
        { 
          timeout: 300000,
          signal: controller.signal
        }
      );
      setMessages(res.data.messages || []);
      setIsPaused(res.data.is_paused || false);
      setPendingAction(res.data.pending_action || null);
    } catch (error) {
      if (axios.isCancel(error)) {
        return;
      }
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

    if (activeAbortController.current) {
      activeAbortController.current.abort();
    }
    const controller = new AbortController();
    activeAbortController.current = controller;

    try {
      const res = await axios.post(
        `${API_BASE}/action`,
        {
          thread_id: threadId,
          action: action,
          reason: action === 'reject' ? 'User rejected execution' : null
        },
        { 
          timeout: 300000,
          signal: controller.signal
        }
      );
      setMessages(res.data.messages || []);
      setIsPaused(res.data.is_paused || false);
      setPendingAction(res.data.pending_action || null);
    } catch (error) {
      if (axios.isCancel(error)) return;
      console.error('Action error:', error);
    } finally {
      setLoading(false);
    }
  };

  const isOnline = connectionStatus === 'online';

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-gray-100 font-sans selection:bg-blue-500/30 overflow-hidden relative">
      {/* Floating Status Capsule */}
      <StatusCapsule status={connectionStatus} />

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col relative min-w-0" role="main">
        <div className="flex-1 overflow-y-auto px-4 pt-20 pb-32">
          {messages.length === 0 && !isPaused && !loading ? (
            <SuggestionGrid 
              onSelectSuggestion={handleSuggestionClick} 
              isOnline={isOnline} 
            />
          ) : (
            <div className="max-w-3xl mx-auto space-y-6 mt-6">
              {messages.filter((m) => m.role !== 'tool' && m.role !== 'system').map((msg, idx) => (
                <ChatMessage 
                  key={`${msg.role}-${idx}-${(msg.content || '').slice(0, 16)}`} 
                  message={msg} 
                />
              ))}

              {loading && (
                <div 
                  role="status" 
                  aria-label="Assistant is thinking"
                  className="flex justify-start px-2 py-3"
                >
                  <div className="flex gap-1.5 items-center">
                    <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}

              {/* Approval UI */}
              {isPaused && pendingAction && (
                <ApprovalCard 
                  onApprove={() => handleApproval('approve')}
                  onReject={() => handleApproval('reject')}
                  loading={loading}
                />
              )}
              <div ref={chatEndRef} className="h-4" />
            </div>
          )}
        </div>

        {/* Input Area */}
        <InputBar 
          input={input}
          onInput={handleInput}
          onSubmit={sendMessage}
          onKeyDown={handleKeyDown}
          textareaRef={textareaRef}
          isPaused={isPaused}
          loading={loading}
          isOnline={isOnline}
        />
      </main>
    </div>
  );
}
