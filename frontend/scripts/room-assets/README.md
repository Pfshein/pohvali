# Room v2 chair assets

Source of the chair artwork rendered from `frontend/public/assets/room/v2/`.

- `chair-back.svg` / `chair-front.svg` — original in-repo vector illustration
  (two perfectly registered layers on one 1000×1000 canvas: back/body/feet
  behind the mascot, rolled arms + seat lip in front).
- `build.mjs` — rasterizes both SVGs to transparent lossless WebP into
  `public/assets/room/v2/` and writes seated-composition previews (390×844 and
  360×667) into the system temp directory for QA.

The chair layers share one 1000×1000 canvas: the seat surface is at y=670 and
the floor contact at y=910. Those two numbers are what `CHAIR_SEAT_POINT` and
`CHAIR_ANCHOR` in `src/features/room/pixi/scenePlan.ts` refer to — change the
art and you must re-tune them together, which is what the previews check.

Everything here is authored for this project; there is no third-party artwork
or license to track.

Rebuild after editing the SVGs (sharp is intentionally not a project
dependency, so install it in a scratch directory and run the script from
there — it resolves every path relative to itself):

```bash
mkdir -p /tmp/room-assets && cd /tmp/room-assets && npm init -y && npm i sharp
node <repo>/frontend/scripts/room-assets/build.mjs
```
