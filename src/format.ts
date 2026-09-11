export function wonToEok(value: string): string {
  const raw = BigInt(value),
    negative = raw < 0n,
    abs = negative ? -raw : raw;
  const rounded = (abs + 500000n) / 1000000n;
  return `${negative ? "−" : ""}${(rounded / 100n).toLocaleString("ko-KR")}.${String(rounded % 100n).padStart(2, "0")}`;
}
export function signedEok(value: string): string {
  return `${BigInt(value) > 0n ? "+" : ""}${wonToEok(value)}`;
}
export function decodeSelection(hash: string) {
  const q = new URLSearchParams(hash.replace(/^#/, ""));
  return {
    company: q.get("company") || "",
    pair: q.get("pair") || "",
    change: q.get("change") || "",
  };
}
export function selectionHash(company: string, pair: string, change = "") {
  const q = new URLSearchParams({ company, pair });
  if (change) q.set("change", change);
  return "#" + q.toString();
}
