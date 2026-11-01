import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user' || message.role === 'human';

  return (
    <article 
      aria-label={`${isUser ? 'User' : 'Assistant'} message`}
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div 
        className={`text-[15px] leading-relaxed max-w-[85%] md:max-w-[75%] ${
          isUser
            ? 'bg-[#2f2f2f] text-white px-5 py-3 rounded-3xl'
            : 'text-gray-200 px-2 py-3'
        }`}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({node, ...props}) => (
                <div className="overflow-x-auto my-4 border border-white/10 rounded-lg">
                  <table className="w-full text-sm text-left border-collapse" {...props} />
                </div>
              ),
              th: ({node, ...props}) => (
                <th className="bg-[#1a1a1a] px-4 py-3 font-medium text-gray-300 border-b border-white/10" {...props} />
              ),
              td: ({node, ...props}) => (
                <td className="px-4 py-3 border-b border-white/5 last:border-0" {...props} />
              ),
              p: ({node, ...props}) => (
                <p className="mb-4 last:mb-0" {...props} />
              ),
              strong: ({node, ...props}) => (
                <strong className="font-semibold text-white" {...props} />
              ),
              ul: ({node, ...props}) => (
                <ul className="list-disc list-inside mb-4 space-y-1" {...props} />
              ),
              ol: ({node, ...props}) => (
                <ol className="list-decimal list-inside mb-4 space-y-1" {...props} />
              ),
              a: ({node, ...props}) => (
                <a 
                  className="text-blue-400 hover:text-blue-300 underline underline-offset-2" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  {...props} 
                />
              )
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </article>
  );
}
