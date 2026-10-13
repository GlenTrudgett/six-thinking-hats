const SYMBOLS: Record<string, string> = {
  USD: "$", AUD: "$", CAD: "$", NZD: "$", SGD: "$", HKD: "$", EUR: "€", GBP: "£",
};

/** Always show the currency code: "AUD $0.0123", never a bare number. */
export function formatMoney(amount: number, currency: string): string {
  return `${currency} ${SYMBOLS[currency] ?? ""}${amount.toFixed(4)}`;
}
