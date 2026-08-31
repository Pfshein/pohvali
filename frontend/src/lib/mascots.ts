export interface StarterMascot {
  code: string;
  name: string;
  blurb: string;
}

// A tiny starter set for the free pick. The full catalog (with stable codes and
// assets) is seeded by PH-401; this list is replaced by those seeds later.
export const STARTER_MASCOTS: StarterMascot[] = [
  { code: "ava", name: "Авокадо Ава", blurb: "Спокойная и тёплая" },
  { code: "pol", name: "Пингвин Поль", blurb: "Неспешный и уютный" },
  { code: "mira", name: "Кошка Мира", blurb: "Мягкая и внимательная" },
];
