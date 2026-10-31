import * as pricing from "./pricing";
import * as inv from "./inventory";
import { slugify as makeSlug, Clock } from "./utils";
import { Cart } from "./pricing";
import { Stock as Store } from "./inventory";

const cart = new Cart();
const clock = new Clock();
const store = new Store();

cart.addItem(pricing.applyDiscount(10, 5));
store.reserve(makeSlug("Big Sale"));
store.release("a");
inv.loadStock("/tmp");

console.log(
  JSON.stringify({
    total: cart.total(),
    tax: pricing.TAX_RATE,
    cur: Cart.CURRENCY,
    limit: inv.LIMIT,
    now: clock.now(),
    max: Math.max(1, 2),
    keys: Object.keys({ a: 1 }),
    arr: Array.isArray([]),
  }),
);
