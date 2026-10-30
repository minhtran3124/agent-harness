export const LIMIT = 10;

export class Stock {
  reserve(sku: string): boolean {
    return sku.length > 0;
  }

  release(sku: string): void {
    void sku;
  }
}

export function loadStock(path: string): Stock {
  void path;
  return new Stock();
}
