# Shot & style library (stop-motion puppet, Coraline look)

Sources are third-party guides (no official Google Veo prompt library found): animationguides.com (shot/angle list), prompt-architects.com (30 lens-specific camera prompts, Veo formula), hypernatural.ai (Coraline look), leonardo.ai/dreamhost Veo 3/3.1 guides, youmind.com/video-prompts (community prompts).

## STYLE BLOCK (append to every img/vid prompt)
`handcrafted stop-motion puppet animation, felt and linen fabric with visible stitching and wear, matte sculpted face with black button eyes, wire-armature posture, miniature practical set with painted backdrop, dramatic stage lighting with deep shadows and warm practical lamps, rich saturated accents against muted earth tones, shallow depth of field, subtle film grain, darkly whimsical, Laika-style, stepped motion at ~12 fps with slight frame-by-frame jerkiness`

## CHARACTER LOCK
See assets/character/hero_passport.md (canonical text, paste verbatim into every request).

## Veo prompt formula
`[camera: shot + angle + lens + move] + [subject] + [action] + [context/set] + [style block]` then, for audio, `Sound: ...` / dialogue in quotes. One dominant camera move, 2-3 modifiers max, clips 4/6/8 s. Always say lens and whether the camera is static.

## Shots (use these words)
| Purpose | Wording |
|---|---|
| Establishing | `wide static establishing shot, 24mm lens, eye-level, no movement` |
| Establishing, push | `slow dolly push from wide to medium shot over the full duration, 35mm` |
| Scale / loneliness | `high-angle wide shot, tiny puppet in a huge empty room, static` |
| Hero / power | `low-angle medium shot, 24mm lens, static` |
| Dialogue | `medium close-up, 35mm lens, eye-level, slight rack focus onto the face` |
| Emotion | `extreme close-up on the button eyes, 85mm lens, shallow depth of field, static` |
| Reaction | `over-the-shoulder framing, 50mm lens, focus on the puppet, static` |
| Profile | `side-profile medium shot, 50mm lens, backlit, silhouette dominates` |
| Following | `medium tracking shot from behind, 35mm lens, 3 ft distance, stepped motion` |
| Walking toward | `low angle 3 ft above ground, 24mm lens, tracking forward as the puppet walks toward camera` |
| Discovery (insert) | `insert shot of an object on a wooden table, macro lens, shallow depth of field, static` |
| POV | `first-person POV, 24mm lens, slow walking pace forward` |
| Unease | `medium close-up, 35mm lens, 15 degree Dutch tilt, static` |
| Reveal | `static medium shot, then slow dolly forward while zooming out` |
| Orbit | `medium close-up, 35mm lens, slow 90 degree orbit` |
| Foreground framing | `medium shot, 50mm lens, sharp silhouetted foreground object framing the puppet` |
| Mirror / reflection | `tight close-up on a reflective surface, puppet visible in reflection, 50mm` |
| Window | `medium shot through a window glass with slight haze, 50mm` |
| Top-down | `God's-eye overhead shot of the puppet lying on the floor among candles` |

## Coraline-specific notes
- Palette: deep blues, vibrant purples, worn browns, dusty greens; warm lamp light against cold shadow.
- Mimic: "replacement face animation": expression changes between discrete sculpted faces, not smooth morphing. Put `no smooth facial morphing, expression changes in discrete steps` in video prompts.
- AI video is naturally smooth; keep `~12 fps stepped motion` and apply an extra 12 fps frame-hold in post (ffmpeg) if Veo is too fluid.
- Keep close-ups of the face rare and short; identity drifts there first. Check every result against the sheet.
