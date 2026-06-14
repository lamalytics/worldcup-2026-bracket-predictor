# 🏆 World Cup 2026 Bracket Predictor

An interactive, visual Streamlit app for predicting the FIFA World Cup 2026 — all 48 teams, from the group stage through to the final. Pick your winners, let the AI fill the gaps by world ranking, and share your road to the trophy.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-ff4b4b)

## Features

- **Group Stage** — all 12 groups (A–L) in a clean grid. Pick the winner and runner-up of each group; the 8 best third-placed teams advance automatically, ranked by points.
- **Knockout Bracket** — Round of 32 → Round of 16 → Quarter-finals → Semi-finals → Final. Click a team to send it through; winners flow left to right.
- **AI Pick** — auto-fills every remaining match using hardcoded FIFA-style world rankings (lower rank number wins).
- **Plotly bracket view** — the full bracket as a connected tree, winners in green, eliminated teams in gray, champion crowned at the top.
- **My Prediction** — your champion shown large with a trophy, their full road to the title, a round-by-round results table, and a copy-paste shareable summary.
- **Country flag emojis** next to every team, dark-friendly UI, and a populated bracket the moment you open it.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually <http://localhost:8501>).

## How qualification works

Each group winner and runner-up advances directly. Third-placed teams are scored with a round-robin model (win = 3, draw = 1, loss = 0) seeded by world ranking, and the **8 best thirds** fill out the 32-team knockout round. Winners are cross-paired against runners-up so no group meets itself in the Round of 32.

## Tech

- **Streamlit** for the UI and `st.session_state` for persisting every pick across pages
- **Plotly** for the bracket tree visualisation
- **pandas** for the standings and results tables
- Single file: [`app.py`](app.py)

## Note on teams

Group assignments are preloaded from the prompt that generated this app and are intended for a fun prediction game, not as official FIFA fixtures. Edit the `GROUPS` dictionary at the top of `app.py` to drop in the real draw whenever you like.
