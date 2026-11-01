import React from 'react';

export default function ApprovalCard({ onApprove, onReject, loading }) {
  return (
    <section 
      role="region"
      aria-label="Pending action approval"
      className="my-6 border border-gray-700 bg-[#1a1a1a] rounded-2xl p-5 md:p-6 shadow-xl"
    >
      <div className="flex items-center gap-3 mb-4">
        <span 
          aria-hidden="true" 
          className="h-2 w-2 rounded-full bg-orange-500 animate-pulse" 
        />
        <h3 className="text-gray-100 font-medium text-sm">Action Approval Required</h3>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <button
          type="button"
          onClick={onApprove}
          disabled={loading}
          aria-label="Approve database update"
          className="flex-1 py-2.5 px-4 bg-white text-black hover:bg-gray-200 font-medium rounded-full text-sm transition disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
        >
          Approve
        </button>
        <button
          type="button"
          onClick={onReject}
          disabled={loading}
          aria-label="Reject database update"
          className="flex-1 py-2.5 px-4 bg-[#2f2f2f] text-white hover:bg-gray-700 font-medium rounded-full text-sm transition disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
        >
          Reject
        </button>
      </div>
    </section>
  );
}
