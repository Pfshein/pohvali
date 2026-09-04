/**
 * Rasterizes the two chair layers to transparent WebP and renders QA previews
 * that composite them with a mascot using the SAME geometry as scenePlan.ts,
 * so the seated composition can be checked before it reaches the app.
 *
 * sharp is deliberately not a project dependency — see README.md for how to
 * run this from a scratch directory.
 */
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { createRequire } from "node:module";

// sharp is not a project dependency, so it is resolved from the working
// directory you installed it in rather than from this script's location.
const sharp = createRequire(join(process.cwd(), "index.mjs"))("sharp");

const here = dirname(fileURLToPath(import.meta.url));
const frontend = resolve(here, "../..");
const outDir = join(frontend, "public/assets/room/v2");
const back = join(here, "chair-back.svg");
const front = join(here, "chair-front.svg");
const mascot = join(frontend, "public/assets/mascots/mira.png");

// Keep in sync with frontend/src/features/room/pixi/scenePlan.ts.
const CHAIR_SIZE_RATIO = 0.92;
const CHAIR_MAX_HEIGHT_RATIO = 0.5;
const CHAIR_ANCHOR = { x: 0.5, y: 0.91 };
const CHAIR_SEAT_POINT = { x: 0.5, y: 0.67 };
const MASCOT_ANCHOR = { x: 0.5, y: 0.88 };
const MASCOT_SIZE_RATIO = 0.55;
// Matches ROOM_SEAT_ANCHOR in catalog/starterRoom.ts.
const SEAT_ANCHOR = { x: 0.5, y: 0.73 };

async function rasterize(svg, name) {
  await sharp(svg, { density: 192 })
    .resize(2000, 2000)
    .webp({ lossless: true })
    .toFile(join(outDir, name));
}

async function preview(width, height, name) {
  const floor = Math.round(height * 0.56);
  const background = Buffer.from(
    `<svg width="${width}" height="${height}">`
    + `<rect width="${width}" height="${floor}" fill="#f6d3a2"/>`
    + `<rect y="${floor}" width="${width}" height="${height - floor}" fill="#e8bd82"/>`
    + `</svg>`,
  );

  const chair = Math.min(CHAIR_SIZE_RATIO * width, CHAIR_MAX_HEIGHT_RATIO * height);
  const pointX = SEAT_ANCHOR.x * width;
  const pointY = SEAT_ANCHOR.y * height;

  const { width: mw, height: mh } = await sharp(mascot).metadata();
  const ratio = mw / mh;
  const box = MASCOT_SIZE_RATIO * chair;
  const mascotWidth = Math.round(ratio >= 1 ? box : box * ratio);
  const mascotHeight = Math.round(ratio >= 1 ? box / ratio : box);
  const mascotY = pointY + (CHAIR_SEAT_POINT.y - CHAIR_ANCHOR.y) * chair;

  const size = Math.round(chair);
  const layer = (svg) => sharp(svg, { density: 192 }).resize(size, size).png().toBuffer();

  await sharp(background)
    .composite([
      {
        input: await layer(back),
        left: Math.round(pointX - CHAIR_ANCHOR.x * chair),
        top: Math.round(pointY - CHAIR_ANCHOR.y * chair),
      },
      {
        input: await sharp(mascot).resize(mascotWidth, mascotHeight).png().toBuffer(),
        left: Math.round(pointX - MASCOT_ANCHOR.x * mascotWidth),
        top: Math.round(mascotY - MASCOT_ANCHOR.y * mascotHeight),
      },
      {
        input: await layer(front),
        left: Math.round(pointX - CHAIR_ANCHOR.x * chair),
        top: Math.round(pointY - CHAIR_ANCHOR.y * chair),
      },
    ])
    .png()
    // QA previews stay out of the repository.
    .toFile(join(tmpdir(), name));
}

await rasterize(back, "chair-back.webp");
await rasterize(front, "chair-front.webp");
await preview(780, 1688, "room-preview-390x844.png");
await preview(720, 1334, "room-preview-360x667.png");

console.log(`wrote chair-back.webp and chair-front.webp to ${outDir}`);
console.log(`wrote QA previews to ${tmpdir()}`);
