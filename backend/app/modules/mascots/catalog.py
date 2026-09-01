from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MascotSeed:
    code: str
    name: str
    blurb: str
    asset_path: str
    starter: bool
    unlock_threshold: int | None
    sort_order: int
    active: bool = True


MASCOT_SEEDS: tuple[MascotSeed, ...] = (
    MascotSeed(
        "ava", "Авокадо Ава", "Спокойная и тёплая", "/assets/mascots/ava.png", True, None, 10
    ),
    MascotSeed(
        "pol", "Пингвин Поль", "Неспешный и уютный", "/assets/mascots/pol.png", True, None, 20
    ),
    MascotSeed(
        "mira", "Кошка Мира", "Мягкая и внимательная", "/assets/mascots/mira.png", True, None, 30
    ),
    MascotSeed(
        "tisha",
        "Капибара Тиша",
        "Добрая и невозмутимая",
        "/assets/mascots/tisha.png",
        False,
        10,
        40,
    ),
    MascotSeed(
        "lumi", "Облачко Луми", "Лёгкое и заботливое", "/assets/mascots/lumi.png", False, 30, 50
    ),
    MascotSeed(
        "bim", "Лягушонок Бим", "Тихий и любопытный", "/assets/mascots/bim.png", False, 100, 60
    ),
)
