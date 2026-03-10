interface TypingIndicatorProps {
  visible: boolean;
}

export default function TypingIndicator({ visible }: TypingIndicatorProps) {
  if (!visible) return null;

  return (
    <div className="flex justify-start px-4">
      <div className="mr-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-100 text-sm">
        🩺
      </div>
      <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-3">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="inline-block h-2 w-2 rounded-full bg-gray-400"
            style={{
              animation: "bounce-dot 1.4s infinite ease-in-out both",
              animationDelay: `${i * 0.16}s`,
            }}
          />
        ))}
        <noscript>
          <span className="text-sm text-gray-500">...</span>
        </noscript>
      </div>
    </div>
  );
}
