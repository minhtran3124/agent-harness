export function slugify(text: string): string {
  return text.toLowerCase().replace(/ /g, "-");
}

export function parseSku(raw: string): string {
  return raw.trim();
}

export class Clock {
  now(): number {
    return Date.now();
  }
}
