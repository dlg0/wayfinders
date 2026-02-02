# Architecture

Treat the tool as a build system:

Inputs:
- Canon YAML (`show/canon/*.yaml`)
- Episode YAML + Shotlist YAML
- Asset packs (cutouts, bgs, overlays)

Outputs:
- plan.json (missing vs referenced)
- timeline.json (Timeline IR)
- renders (frames, animatic.mp4, final.mp4)
- provenance bundle (zip)

Key constraints:
- Option B cutouts: characters generated once (pose packs), reused per shot
- Cacheability: stable cache keys
- Provenance: sidecar metadata + JSONL logs per episode
