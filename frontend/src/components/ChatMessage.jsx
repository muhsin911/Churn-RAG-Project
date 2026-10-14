import { Bot, UserRound } from "lucide-react";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <span
        className={`mt-1 grid size-9 shrink-0 place-items-center rounded-xl ${
          isUser ? "bg-brand text-white" : "bg-brand-soft text-brand"
        }`}
        aria-hidden="true"
      >
        {isUser ? <UserRound size={17} /> : <Bot size={18} />}
      </span>
      <div className={`max-w-[85%] ${isUser ? "text-right" : ""}`}>
        <p
          className={`inline-block whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${
            isUser
              ? "rounded-tr-md bg-brand text-white"
              : "rounded-tl-md border border-slate-200 bg-white text-ink"
          }`}
        >
          {message.content}
        </p>
        {!isUser && message.sources?.length > 0 && (
          <p className="mt-2 text-left text-xs text-muted">
            Sources: {message.sources.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}