export const TAX_RATE = 0.2;

export function applyDiscount(price: number, pct: number): number {
  return price * (1 - pct / 100);
}

export function formatPrice(value: number): string {
  return value.toFixed(2);
}

export class Cart {
  static CURRENCY = "EUR";
  items: number[] = [];

  addItem(item: number): void {
    this.items.push(item);
  }

  total(): number {
    return this.items.reduce((a, b) => a + b, 0);
  }

  clear(): void {
    this.items = [];
  }
}
