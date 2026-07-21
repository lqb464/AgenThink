"use client";

export function TypingIndicator() {
  return (
    <div className="msg-row bot msg-in flex justify-start px-4 py-2 w-full">
      <div className="typing-indicator">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <span className="typing-text">Đang suy nghĩ...</span>
      </div>
    </div>
  );
}
