# Wayfinders CLI Templates

Jinja2 templates for scaffolding new episodes via `wf new-episode`.

## Template Parameters

All templates receive the following parameters:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `ep_id` | `str` | Episode identifier (format: `sXXeYY`) | `"s01e05"` |
| `title` | `str` | Episode title | `"The Lost Compass"` |
| `biome` | `str` | Environment biome ID | `"windglass_plains"` |
| `runtime_target_sec` | `int` | Target runtime in seconds | `780` |
| `cast` | `list[str]` | Character IDs | `["charlie", "spencer", "fletcher", "fold"]` |
| `style_profile` | `str` | Style profile ID | `"comic_low_fps_v1"` |

## Templates

### episode.yaml.j2

Generates the main episode configuration file. Produces YAML compatible with the `Episode` Pydantic model in `schema.py`.

**Derived values:**
- `pose_packs`: Auto-generated as `posepack_{character}_v1` for each cast member
- `bg_pack`: Auto-generated as `{biome}_v1`
- `overlay_pack`: Default `"overlays_v1"`

### shotlist.yaml.j2

Generates an initial shotlist with example shots. Produces YAML compatible with the `ShotList` Pydantic model.

**Includes:**
- Opening establishing shot with camera pan
- Second shot featuring the first cast member

### README.md.j2

Generates episode documentation with sections for:
- Logline
- Notes (biome, runtime, style)
- Cast list
- Development status checklist

## Usage

Templates are rendered with Jinja2's `StrictUndefined` environment to catch missing parameters early:

```python
from jinja2 import Environment, PackageLoader, StrictUndefined

env = Environment(
    loader=PackageLoader("wayfinders_cli", "templates"),
    undefined=StrictUndefined,
)
template = env.get_template("episode.yaml.j2")
content = template.render(
    ep_id="s01e05",
    title="The Lost Compass",
    biome="windglass_plains",
    runtime_target_sec=780,
    cast=["charlie", "spencer", "fletcher", "fold"],
    style_profile="comic_low_fps_v1",
)
```
