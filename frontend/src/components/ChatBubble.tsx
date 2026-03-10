import type { Message } from "../types/chat";

interface ChatBubbleProps {
  message: Message;
}

export default function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";

  const bubbleBase = "max-w-[80%] md:max-w-[70%] px-4 py-3 text-sm md:text-base whitespace-pre-wrap break-words";

  let bubbleStyle: string;
  if (isUser) {
    bubbleStyle = `${bubbleBase} rounded-2xl bg-teal-500 text-white`;
  } else if (message.warningLevel === "Critical") {
    bubbleStyle = `${bubbleBase} rounded-2xl rounded-tl-sm bg-red-50 border-2 border-red-400 text-gray-900`;
  } else if (message.warningLevel === "Caution") {
    bubbleStyle = `${bubbleBase} rounded-2xl rounded-tl-sm bg-orange-50 border-2 border-orange-400 text-gray-900`;
  } else {
    bubbleStyle = `${bubbleBase} rounded-2xl rounded-tl-sm bg-gray-100 text-gray-900`;
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} px-4`}>
      {!isUser && (
        <div className="mr-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-100 text-sm">
          🩺
        </div>
      )}
      <div className={bubbleStyle}>{message.content}</div>
    </div>
  );
}
