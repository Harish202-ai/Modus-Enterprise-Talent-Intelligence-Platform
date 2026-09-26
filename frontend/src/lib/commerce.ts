import { apiFetch } from "./api";

export type Product = {
  key: string;
  version: number;
  name: string;
  kind: "assessment" | "bundle" | "report_upgrade";
  description: string | null;
  price: number;
  currency: string;
  assessment_keys: string[];
  assessments?: { key: string; name: string }[];
  bundled_product_keys: string[];
  requires_product_keys: string[];
};

export type Payment = {
  id: string;
  product_key: string;
  amount: number;
  currency: string;
  status: "pending" | "paid" | "expired" | "failed" | "amount_mismatch";
  created_at: string;
  paid_at: string | null;
};

export type MyEntitlements = {
  products: (Product & { granted_at: string; source: string })[];
  assessment_keys: string[];
  payments: Payment[];
};

export const commerceApi = {
  products: () => apiFetch<Product[]>("/v1/products"),
  mine: () => apiFetch<MyEntitlements>("/v1/entitlements/me"),
  checkout: (productKey: string) =>
    apiFetch<{ payment_id?: string; checkout_url: string | null; free?: boolean }>("/v1/payments/checkout", {
      method: "POST",
      body: JSON.stringify({ product_key: productKey }),
    }),
  confirm: (sessionId: string) => apiFetch<Payment>("/v1/payments/confirm", { method: "POST", body: JSON.stringify({ session_id: sessionId }) }),
};

export function formatPrice(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: amount % 1 ? 2 : 0 }).format(amount);
  } catch {
    return `${currency} ${amount}`;
  }
}
