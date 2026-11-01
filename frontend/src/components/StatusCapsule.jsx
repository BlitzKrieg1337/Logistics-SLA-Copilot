import React from 'react';

const STATUS_CONFIG = {
  checking: { dot: 'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.5)]', text: 'Connecting…' },
  waking:   { dot: 'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.5)] animate-pulse', text: 'Waking up server…' },
  online:   { dot: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]', text: 'Connected' },
  offline:  { dot: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]', text: 'Offline' },
};

export default function StatusCapsule({ status }) {
  const current = STATUS_CONFIG[status] || STATUS_CONFIG.checking;

  return (
    <aside 
      aria-label="System status"
      className="absolute top-5 left-5 z-50"
    >
      <div 
        role="status"
        aria-live="polite"
        className="flex items-center gap-2 px-3 py-1.5 bg-[#171717]/80 backdrop-blur-md rounded-full border border-white/5 shadow-md"
      >
        <span 
          aria-hidden="true" 
          className={`w-2 h-2 rounded-full ${current.dot}`} 
        />
        <span className="text-xs font-medium text-gray-300">
          {current.text}
        </span>
      </div>
    </aside>
  );
}
