// "Wren": an original little bird who reads. Simple geometric shapes, navy + cream + one golden accent.
// Decorative only: always aria-hidden. Use sparingly (home greeting, loading, empty states,
// sign-in, onboarding). Never inside an answer, a citation, or the evidence label.
export type MascotState = "idle" | "thinking" | "pointing" | "nothing";

const INK = "var(--color-ink)";
const NAVY = "var(--color-primary)";
const CREAM = "var(--color-warm)";
const GOLD = "var(--color-highlight)";

function Eyes({
  look = "center",
  brow = false,
}: {
  look?: "center" | "up" | "right" | "down";
  brow?: boolean;
}) {
  const dx = look === "right" ? 2.5 : 0;
  const dy = look === "up" ? -2.5 : look === "down" ? 2 : 0;
  return (
    <g>
      <g className="wren-eyes">
        <circle cx="47" cy="56" r="7.5" fill="#fff" />
        <circle cx="73" cy="56" r="7.5" fill="#fff" />
        <circle cx={47 + dx} cy={56 + dy} r="3.6" fill={INK} />
        <circle cx={73 + dx} cy={56 + dy} r="3.6" fill={INK} />
      </g>
      {brow && (
        <g stroke={CREAM} strokeWidth="2.5" strokeLinecap="round" fill="none">
          <path d="M39 47 L53 43" />
          <path d="M81 47 L67 43" />
        </g>
      )}
    </g>
  );
}

function Book({ open = false }: { open?: boolean }) {
  return open ? (
    <g>
      <path
        d="M30 88 L60 84 L90 88 L90 108 L60 104 L30 108 Z"
        fill="#fff"
        stroke={NAVY}
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <path d="M60 84 V104" stroke={NAVY} strokeWidth="2.5" />
      <path
        d="M38 94 H52 M38 100 H48"
        stroke={NAVY}
        strokeOpacity="0.25"
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray="1 5"
      />
    </g>
  ) : (
    <g>
      <rect
        x="36"
        y="86"
        width="48"
        height="22"
        rx="4"
        fill="#fff"
        stroke={NAVY}
        strokeWidth="2.5"
      />
      <path d="M60 86 V108" stroke={NAVY} strokeWidth="2.5" />
      <path
        d="M42 94 H54 M66 94 H78 M42 100 H50 M66 100 H74"
        stroke={NAVY}
        strokeOpacity="0.3"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </g>
  );
}

export function Mascot({
  state = "idle",
  size = 120,
  className = "",
}: {
  state?: MascotState;
  size?: number;
  className?: string;
}) {
  const tilt = state === "thinking" ? -7 : state === "nothing" ? 6 : 0;
  return (
    <svg
      viewBox="0 0 130 120"
      width={size}
      height={(size * 120) / 130}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <g className={state === "idle" ? "wren-bob" : undefined}>
        {/* feet */}
        <path
          d="M50 108 V114 M44 114 H56 M70 108 V114 M64 114 H76"
          stroke={GOLD}
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />
        <g
          transform={`rotate(${tilt} 60 70)`}
          style={{ transition: "transform 320ms var(--ease)" }}
        >
          {/* head tuft */}
          <path d="M54 32 q2 -12 8 -9 q-1 6 4 9 Z" fill={NAVY} />
          {/* body */}
          <path
            d="M60 30 C88 30 100 52 98 74 C96 98 80 108 60 108 C40 108 24 98 22 74 C20 52 32 30 60 30 Z"
            fill={NAVY}
          />
          {/* belly */}
          <path
            d="M60 70 C78 70 86 82 84 94 C82 104 72 108 60 108 C48 108 38 104 36 94 C34 82 42 70 60 70 Z"
            fill={CREAM}
          />
          <Eyes
            look={
              state === "thinking"
                ? "up"
                : state === "pointing"
                  ? "right"
                  : state === "nothing"
                    ? "down"
                    : "center"
            }
            brow={state === "nothing"}
          />
          {/* beak */}
          <path d="M53 65 L67 65 L60 76 Z" fill={GOLD} />
        </g>
        <Book open={state === "nothing"} />
        {state === "pointing" && (
          <g>
            <path
              d="M92 76 Q110 74 118 56"
              stroke={NAVY}
              strokeWidth="10"
              strokeLinecap="round"
              fill="none"
            />
            <circle cx="118" cy="54" r="5" fill={GOLD} />
          </g>
        )}
        {state === "thinking" && (
          <g fill={NAVY}>
            <circle className="wren-dot" cx="98" cy="22" r="3.5" />
            <circle
              className="wren-dot"
              cx="108"
              cy="14"
              r="3.5"
              style={{ animationDelay: "0.2s" }}
            />
            <circle
              className="wren-dot"
              cx="118"
              cy="6"
              r="3.5"
              style={{ animationDelay: "0.4s" }}
            />
          </g>
        )}
      </g>
    </svg>
  );
}
