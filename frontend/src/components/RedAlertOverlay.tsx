import { createPortal } from "react-dom";

const CRISIS_CONTACTS = [
  { name: "자살예방상담전화", number: "1393", desc: "24시간" },
  { name: "정신건강위기상담", number: "1577-0199", desc: "" },
  { name: "생명의전화", number: "1588-9191", desc: "" },
];

interface RedAlertOverlayProps {
  visible: boolean;
  message: string | null;
  onClose: () => void;
}

export default function RedAlertOverlay({
  visible,
  message,
  onClose,
}: RedAlertOverlayProps) {
  if (!visible) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-red-900/80 p-4"
      style={{
        animation: "red-pulse 1s ease-in-out 3",
      }}
      role="alertdialog"
      aria-label="위기 상황 경고"
    >
      <div className="flex w-full max-w-sm flex-col items-center gap-6">
        {/* Message */}
        <div className="text-center">
          <p className="mb-2 text-2xl font-bold text-white">
            지금 많이 힘드시군요
          </p>
          <p className="text-sm text-red-100">
            전문가가 도와드릴 수 있습니다.
          </p>
        </div>

        {/* Crisis contacts */}
        <div className="flex w-full flex-col gap-3">
          {CRISIS_CONTACTS.map((contact) => (
            <a
              key={contact.number}
              href={`tel:${contact.number}`}
              className="flex flex-col items-center rounded-xl bg-white p-4 shadow-lg transition-transform active:scale-95"
            >
              <span className="text-sm font-medium text-gray-600">
                {contact.name}
                {contact.desc && (
                  <span className="ml-1 text-xs text-gray-400">
                    ({contact.desc})
                  </span>
                )}
              </span>
              <span className="mt-1 text-2xl font-bold text-red-600">
                {contact.number}
              </span>
            </a>
          ))}
        </div>

        {/* Response message (collapsed) */}
        {message && (
          <div className="max-h-32 w-full overflow-y-auto rounded-lg bg-red-800/50 p-3 text-xs text-red-100">
            {message}
          </div>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          className="rounded-full bg-white/20 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-white/30"
        >
          대화로 돌아가기
        </button>
      </div>
    </div>,
    document.body,
  );
}
