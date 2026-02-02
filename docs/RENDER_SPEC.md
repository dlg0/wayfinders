# Render spec (Option B cutouts)

Outputs:
- renders/frames/frame_000001.png ...
- renders/animatic.mp4
- renders/final.mp4
- logs/timeline.json
- logs/render_report.json

Frame synthesis:
- BG: assets/bgs/<bg>.png or layered versions (<bg>__fg.png etc.)
- Camera: pan/slowpush/shake
- Actors: cutouts assets/chars/<char>/<pose>_<expr>.png
- Default stage layout if actor transforms not specified
- Overlays: text (v1) or bitmaps (v2)
- FX: simple overlays/masks (v1), expand over time

MP4:
- Prefer ffmpeg; provide frames-only fallback if ffmpeg missing.
