# How this profile is built

Every graphic on the profile is an SVG generated in this repository. Nothing
on the page requests anything from a third party, so nothing on the page can
rate-limit, 503, or quietly change theme on someone else's schedule.

```
portrait.svg      the ASCII portrait, typed in once on load
stats.svg         contributions in the last 365 days + a weekly sparkline
streak.svg        current streak, longest streak, days with a commit
langs.svg         languages by share of bytes across public repositories
year.svg          the last 365 days, one character per day
hd-*.svg          section headings
```

The four data cards are redrawn nightly by [`.github/workflows/refresh-stats.yml`](.github/workflows/refresh-stats.yml).
The portrait and the headings are static; regenerate them by hand when the
photo or the section list changes.

## What GitHub allows in a README

This dictates every decision below. Verified by posting the README to
GitHub's own rendering API (`POST /markdown`) and reading back what survived.

| | |
| --- | --- |
| **stripped** | `<style>` blocks · `style=` · `class=` · inline `<svg>` · `<script>` |
| **kept** | `<img>` · `<samp>` · `<sub>` · `<sup>` · `<kbd>` · `<blockquote>` · `<details>` · `<br>` · `align=` · `width=` |

Three things follow from that:

1. **README text cannot change typeface.** Only GitHub's sans or its mono, via
   backticks or a `<samp>` tag. Anything in another face has to be an image.
2. **Motion has to live inside the SVG.** Scripts are stripped, so the typing
   animation is SMIL — `<animate>` and `<set>` — which GitHub does run.
3. **Section headings are images**, which is the only way to set them in
   JetBrains Mono. The cost is real and worth stating: an image heading has no
   anchor, so the README outline is empty. The `alt` text carries the word.

## First-time setup

The repository has to be named exactly your GitHub username — that is what
makes its README the profile README.

```bash
gh repo create <your-username> --public --source=. --push
# or create it on github.com and: git remote add origin ... && git push -u origin main
```

Then open **Actions → refresh stats → Run workflow** once. It needs no personal
access token: the built-in `GITHUB_TOKEN` returns the same numbers. After that
it runs itself at 05:17 UTC daily.

## Running the generators

```bash
pip install pillow numpy opencv-python-headless rembg onnxruntime fonttools brotli

python3 scripts/build_fonts.py                    # subset the fonts (rarely)
python3 scripts/make_portrait.py                  # portrait.svg
python3 scripts/make_headings.py                  # hd-*.svg
GH_LOGIN=<you> GITHUB_TOKEN=<token> python3 scripts/generate_stats.py
```

`generate_stats.py` imports nothing outside the standard library — that is the
point, since it is the one that runs in CI. The other three are development
tools and never run there.

### A new photo

```bash
python3 scripts/make_portrait.py new.jpg portrait.svg --crop 0.23,0.02,0.76,0.63
```

`--crop` is left,top,right,bottom as fractions of the source. Crop tight, hair
line to just under the chin. ASCII draws with shadow and has thirteen levels to
do it with; a face filling 30% of the frame will not resolve, and a shirt in
the frame fills half the grid with mid-tone noise that competes with the face.
Side light at roughly 45° beats flat frontal light, which renders as one tone.

`--gamma` is the darkening curve. 1.7 suits the current photo; lower flattens
the features, higher blocks the face into a silhouette.

### New text

Body copy lives in `README.md`. Section names live in `SECTIONS` in
`scripts/make_headings.py` — edit the list and re-run it.

## Decisions worth keeping

**The window is pinned to whole UTC days.** Left alone,
`contributionsCollection` measures "the past year" from the instant of the
request, so two runs minutes apart bucket days into different weeks and the
sparkline shifts by a fraction of a pixel. That is enough to produce a commit
every night that means nothing.

**Repositories are filtered to `privacy: PUBLIC`.** A personal token sees
private repositories and the workflow's token does not, so without the filter
the language split depends on who ran the script.

**The workflow has no `push` trigger.** It commits; a push trigger would set it
running again on its own commit.

**It commits only when a file actually changed**, or the profile collects a
commit every night whether or not anything moved.

**Let the action own the four data cards.** Regenerating them locally as well
guarantees conflicts — your token and the workflow's bucket a day near a week
boundary differently, so the output is never byte-identical.

**Columns, not a line, for daily counts.** Daily contributions are sparse and
discrete; a line through `0, 0, 11, 0, 0, 10` claims values that never existed.
The sparkline is a *weekly* aggregate, where continuity is defensible.

**One fill colour, and colours that survive both themes.** README images cannot
see `prefers-color-scheme` — they are `<img>` documents — so a single palette
has to clear 3:1 contrast on `#ffffff` and on `#0d1117` alike. Hierarchy comes
from opacity, not from lightness. Per-character rainbow colouring is what makes
most ASCII portraits look like static.

**Fonts are inlined as base64.** An external font URL cannot work: browsers
refuse subresource fetches for image documents, so a `<link>` or a plain
`@font-face` URL loads nothing. Every SVG carries its own subset — 1.2 KB for
the thirteen ramp characters, 3.5 KB for basic latin — which is why the whole
page is about 60 KB of font rather than several megabytes. JetBrains Mono is
600/1000 units, exactly the 0.600 em the character grid assumes, so nothing
about the geometry changes. It is under the SIL OFL; the licence ships in
`assets/fonts/OFL.txt`. A commercial font could not go in a public repo.

## Traps hit while building this

- **A `<style>` rule beats a presentation attribute.** `text{font-size:12.9px}`
  in the SVG's own stylesheet silently overrode every `font-size="11.5"` on a
  tag, and the legend ran into its label. Sizes that differ from the default
  have to be classes.
- **GitHub turns every newline inside a paragraph into a `<br>`.** Writing your
  own `<br>` at the end of each line doubles the leading.
- **`rembg`'s default model is now about 1 GB.** `new_session("u2net_human_seg")`
  gets a 176 MB one trained on people, which is the better choice here anyway.
- **A python.org install has no CA certificates**, so `urllib` fails to verify
  api.github.com. Run `Install Certificates.command` from the Python folder, or
  run the generator in CI where it is not an issue.
- **Headless screenshots do not advance SMIL.** `--virtual-time-budget` does not
  move the animation clock, and a negative `begin` is not a substitute — Chrome
  drops animations that finished before document time zero. Inline the SVG in a
  page and call `svg.setCurrentTime(6)`, then screenshot.
- **Pinned repositories and the profile bio cannot be set through the API.** No
  GraphQL mutation exists. Both are manual, in the UI.
- **A newly created profile README is cached.** If it does not appear on the
  profile, edit it once through the web UI to force a refresh.

## Credit

The portrait pipeline follows the approach in *A GitHub profile that generates
itself* and the ASCII Portrait README Guide it credits. Typeface: JetBrains
Mono, SIL OFL 1.1.
