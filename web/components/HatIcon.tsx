import type { Hat } from "@/lib/types";

export type AnyHat = Hat | "blue";

// Hat colours measured from the book cover (see PALETTE.md).
export const HAT_COLOUR: Record<AnyHat, string> = {
  white: "#f3eeee",
  red: "#c2262e",
  green: "#3b671a",
  yellow: "#e7a601",
  black: "#272331",
  blue: "#0179d5",
};

const OUTLINE = "#272331";

/** A small hat drawn for the UI: a bowler for black, a fedora for the rest. */
export function HatIcon({ hat, size = 28 }: { hat: AnyHat; size?: number }) {
  const fill = HAT_COLOUR[hat];
  const bowler = hat === "black";
  return (
    <svg
      width={size}
      height={size * 0.75}
      viewBox="0 0 48 36"
      role="img"
      aria-label={`${hat} hat`}
      className="hat-icon"
    >
      <ellipse cx="24" cy="26" rx="22" ry="7" fill={fill} stroke={OUTLINE} strokeWidth="1.6" />
      {bowler ? (
        <path d="M11 25 C10 6 38 6 37 25 Z" fill={fill} stroke={OUTLINE} strokeWidth="1.6" />
      ) : (
        <path
          d="M10.5 25 C9 12 15 5 20 6 Q24 9 28 6 C33 5 39 12 37.5 25 Z"
          fill={fill}
          stroke={OUTLINE}
          strokeWidth="1.6"
        />
      )}
      <path d="M10.6 21 H37.4 V25 H10.6 Z" fill={OUTLINE} opacity={hat === "black" ? 0.55 : 0.3} />
    </svg>
  );
}

/** A pill: the hat and its name. */
export function HatChip({ hat, label }: { hat: AnyHat; label?: string }) {
  return (
    <span className={`chip ${hat}`}>
      <HatIcon hat={hat} size={22} />
      <span>{label ?? hat}</span>
    </span>
  );
}
