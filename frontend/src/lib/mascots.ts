export interface Mascot {
  code: string;
  name: string;
  blurb: string;
  assetPath: string;
  starter: boolean;
}

export const MASCOTS: readonly Mascot[] = [
  {
    code: "ava",
    name: "Авокадо Ава",
    blurb: "Спокойная и тёплая",
    assetPath: "/assets/mascots/ava.png",
    starter: true,
  },
  {
    code: "pol",
    name: "Пингвин Поль",
    blurb: "Неспешный и уютный",
    assetPath: "/assets/mascots/pol.png",
    starter: true,
  },
  {
    code: "mira",
    name: "Кошка Мира",
    blurb: "Мягкая и внимательная",
    assetPath: "/assets/mascots/mira.png",
    starter: true,
  },
  {
    code: "tisha",
    name: "Капибара Тиша",
    blurb: "Добрая и невозмутимая",
    assetPath: "/assets/mascots/tisha.png",
    starter: false,
  },
  {
    code: "lumi",
    name: "Облачко Луми",
    blurb: "Лёгкое и заботливое",
    assetPath: "/assets/mascots/lumi.png",
    starter: false,
  },
  {
    code: "bim",
    name: "Лягушонок Бим",
    blurb: "Тихий и любопытный",
    assetPath: "/assets/mascots/bim.png",
    starter: false,
  },
];

export const STARTER_MASCOTS = MASCOTS.filter((mascot) => mascot.starter);

export function findMascot(code: string | null | undefined): Mascot {
  return MASCOTS.find((mascot) => mascot.code === code) ?? STARTER_MASCOTS[0]!;
}
