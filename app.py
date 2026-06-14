"""
World Cup 2026 Bracket Predictor
A fast, visual, interactive Streamlit app for predicting the 48-team
FIFA World Cup 2026 from the group stage through to the final.

Run with:  streamlit run app.py
"""

import json

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------------------------------- #
#  Page config + theme
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="World Cup 2026 Bracket Predictor",
    page_icon="🏆",
    layout="wide",
)

CSS = """
<style>
    .block-container { padding-top: 2.2rem; }
    .wc-title {
        font-size: 2.5rem; font-weight: 800; letter-spacing: -1px;
        background: linear-gradient(90deg, #00c2a8, #2bd576 55%, #ffd54a);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .wc-sub { color: #9aa4b2; font-size: 1rem; margin-top: .15rem; }
    .champ-card {
        text-align:center; padding: 1.6rem 1rem; border-radius: 18px;
        background: radial-gradient(circle at 50% 0%, rgba(43,213,118,.22), rgba(43,213,118,.03) 70%);
        border: 1px solid rgba(43,213,118,.45);
    }
    .champ-name { font-size: 2.7rem; font-weight: 800; color: #2bd576; line-height:1.1; }
    .champ-trophy { font-size: 3.6rem; }
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.08);
        padding: .6rem .9rem; border-radius: 12px;
    }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  Static data — 48 teams in 12 groups (spellings normalised to FIFA usage)
# --------------------------------------------------------------------------- #
GROUPS = {
    "A": ["Mexico", "South Korea", "Czechia", "South Africa"],
    "B": ["Switzerland", "Canada", "Qatar", "Bosnia and Herzegovina"],
    "C": ["Scotland", "Morocco", "Brazil", "Haiti"],
    "D": ["USA", "Turkey", "Australia", "Paraguay"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cabo Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

FLAGS = {
    "Mexico": "🇲🇽", "South Korea": "🇰🇷", "Czechia": "🇨🇿", "South Africa": "🇿🇦",
    "Switzerland": "🇨🇭", "Canada": "🇨🇦", "Qatar": "🇶🇦", "Bosnia and Herzegovina": "🇧🇦",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Morocco": "🇲🇦", "Brazil": "🇧🇷", "Haiti": "🇭🇹",
    "USA": "🇺🇸", "Turkey": "🇹🇷", "Australia": "🇦🇺", "Paraguay": "🇵🇾",
    "Germany": "🇩🇪", "Curacao": "🇨🇼", "Ivory Coast": "🇨🇮", "Ecuador": "🇪🇨",
    "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Sweden": "🇸🇪", "Tunisia": "🇹🇳",
    "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿",
    "Spain": "🇪🇸", "Cabo Verde": "🇨🇻", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾",
    "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶", "Norway": "🇳🇴",
    "Argentina": "🇦🇷", "Algeria": "🇩🇿", "Austria": "🇦🇹", "Jordan": "🇯🇴",
    "Portugal": "🇵🇹", "DR Congo": "🇨🇩", "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Croatia": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
    # ranking-only teams (not in any group, kept for completeness)
    "Italy": "🇮🇹", "Denmark": "🇩🇰",
}

# FIFA-style seed order used for the "AI Pick" feature (lower number = stronger).
_RANK_ORDER = [
    "France", "Brazil", "England", "Argentina", "Portugal", "Spain", "Belgium",
    "Netherlands", "Germany", "Italy", "Croatia", "Denmark", "Uruguay", "USA",
    "Mexico", "Morocco", "Colombia", "Japan", "South Korea", "Senegal",
]
RANKINGS = {team: i + 1 for i, team in enumerate(_RANK_ORDER)}
UNRANKED = 99

ROUND_NAMES = ["Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final"]


def rank(team):
    if team is None:
        return UNRANKED + 1
    return RANKINGS.get(team, UNRANKED)


def label(team):
    """Flag + name, with a graceful fallback for empty slots."""
    if not team:
        return "—"
    return f"{FLAGS.get(team, '🏳️')} {team}"


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# --------------------------------------------------------------------------- #
#  Group-stage maths
# --------------------------------------------------------------------------- #
def group_points(teams):
    """Round-robin points (W=3, D=1, L=0) where the better-ranked team wins.
    Two unranked teams draw. Used only to seed the best-third-place race."""
    pts = {t: 0 for t in teams}
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            a, b = teams[i], teams[j]
            ra, rb = rank(a), rank(b)
            if ra < rb:
                pts[a] += 3
            elif rb < ra:
                pts[b] += 3
            else:
                pts[a] += 1
                pts[b] += 1
    return pts


def init_group_state():
    for g, teams in GROUPS.items():
        ranked = sorted(teams, key=rank)
        st.session_state.setdefault(f"first_{g}", ranked[0])
        st.session_state.setdefault(f"second_{g}", ranked[1])


def third_place_df():
    """Best third-placed team per group, ranked across all groups."""
    rows = []
    for g, teams in GROUPS.items():
        pts = group_points(teams)
        first = st.session_state[f"first_{g}"]
        second = st.session_state[f"second_{g}"]
        rest = [t for t in teams if t not in (first, second)]
        rest.sort(key=lambda t: (-pts[t], rank(t)))
        third = rest[0]
        rows.append({"Group": g, "Team": third, "Pts": pts[third], "_r": rank(third)})
    df = pd.DataFrame(rows).sort_values(["Pts", "_r"], ascending=[False, True])
    df = df.reset_index(drop=True)
    df["Advances"] = [i < 8 for i in range(len(df))]
    return df


def qualified_thirds():
    df = third_place_df()
    return list(df[df["Advances"]]["Team"])


# --------------------------------------------------------------------------- #
#  Knockout bracket
# --------------------------------------------------------------------------- #
def seed_r32():
    """Return the 32 qualified teams in match order [m0a, m0b, m1a, m1b, ...].
    Winners are cross-paired with runners-up to avoid same-group rematches."""
    W = {g: st.session_state[f"first_{g}"] for g in GROUPS}
    R = {g: st.session_state[f"second_{g}"] for g in GROUPS}
    T = qualified_thirds()
    T = (T + [None] * 8)[:8]

    pairs = [
        (W["A"], R["B"]), (W["C"], R["D"]), (W["E"], R["F"]), (W["G"], R["H"]),
        (W["I"], R["J"]), (W["K"], R["L"]),
        (W["B"], R["A"]), (W["D"], R["C"]), (W["F"], R["E"]), (W["H"], R["G"]),
        (W["J"], R["I"]), (W["L"], R["K"]),
        (T[0], T[1]), (T[2], T[3]), (T[4], T[5]), (T[6], T[7]),
    ]
    flat = []
    for a, b in pairs:
        flat.extend([a, b])
    return flat


def get_pick(r, i, a, b):
    """Stored winner for a match, validated against its current two teams."""
    key = f"pick_{r}_{i}"
    val = st.session_state.get(key)
    if val in (a, b) and val is not None:
        return val
    return None


def build_rounds():
    """Return (rounds, champion). rounds[r] is a list of (teamA, teamB, winner)."""
    column = seed_r32()
    rounds = []
    for r in range(5):
        n = len(column) // 2
        matches, winners = [], []
        for i in range(n):
            a, b = column[2 * i], column[2 * i + 1]
            w = get_pick(r, i, a, b)
            matches.append((a, b, w))
            winners.append(w)
        rounds.append(matches)
        column = winners
    champion = rounds[-1][0][2]
    return rounds, champion


def ai_winner(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return a if rank(a) <= rank(b) else b


def autofill(overwrite):
    """Fill matches by FIFA rank. overwrite=True replaces existing picks."""
    column = seed_r32()
    for r in range(5):
        n = len(column) // 2
        winners = []
        for i in range(n):
            a, b = column[2 * i], column[2 * i + 1]
            key = f"pick_{r}_{i}"
            cur = st.session_state.get(key)
            if overwrite or cur not in (a, b) or cur is None:
                st.session_state[key] = ai_winner(a, b)
            winners.append(st.session_state[key])
        column = winners


def set_pick(r, i, team):
    st.session_state[f"pick_{r}_{i}"] = team
    # Invalidate any downstream picks that no longer have valid teams feeding them.
    _, _ = build_rounds()


# --------------------------------------------------------------------------- #
#  Shareable bracket codes  (group picks + 31 knockout results -> URL string)
# --------------------------------------------------------------------------- #
KNOCKOUT_COUNTS = [16, 8, 4, 2, 1]


def encode_bracket():
    """Compact code: 12 groups (2 digits each) + '-' + 31 trits for knockouts.
    Each knockout trit is 0 (top team), 1 (bottom team) or 2 (unpicked)."""
    grp = []
    for g, teams in GROUPS.items():
        first = st.session_state.get(f"first_{g}")
        second = st.session_state.get(f"second_{g}")
        fi = teams.index(first) if first in teams else 0
        si = teams.index(second) if second in teams else (1 if fi != 1 else 0)
        grp.append(f"{fi}{si}")
    rounds, _ = build_rounds()
    trits = []
    for r in range(5):
        for (a, b, w) in rounds[r]:
            trits.append("0" if w == a and w is not None
                         else "1" if w == b and w is not None else "2")
    return "".join(grp) + "-" + "".join(trits)


def apply_bracket(code):
    """Inverse of encode_bracket. Writes picks into session_state. Safe on junk."""
    try:
        grp, ko = code.split("-")
        groups = list(GROUPS.items())
        if len(grp) != 2 * len(groups):
            return False
        for idx, (g, teams) in enumerate(groups):
            fi = int(grp[2 * idx])
            si = int(grp[2 * idx + 1])
            first = teams[fi % 4]
            second = teams[si % 4]
            if second == first:
                second = next(t for t in teams if t != first)
            st.session_state[f"first_{g}"] = first
            st.session_state[f"second_{g}"] = second
        # Rebuild the knockout structure from the freshly-set group picks and
        # apply each trit in the same order encode_bracket produced them.
        column = seed_r32()
        ti = 0
        for r in range(5):
            n = len(column) // 2
            winners = []
            for i in range(n):
                a, b = column[2 * i], column[2 * i + 1]
                t = ko[ti] if ti < len(ko) else "2"
                ti += 1
                w = a if t == "0" else b if t == "1" else None
                if w not in (a, b):
                    w = None
                st.session_state[f"pick_{r}_{i}"] = w
                winners.append(w)
            column = winners
        return True
    except (ValueError, IndexError, KeyError):
        return False


# --------------------------------------------------------------------------- #
#  Plotly bracket visualisation
# --------------------------------------------------------------------------- #
def bracket_figure(rounds, champion, for_export=False):
    """Left-to-right bracket tree. Columns are teams advancing each round.
    for_export=True adds a title and a solid dark background for a clean
    downloadable HTML file."""
    # Column 0 = the 32 seeded teams; columns 1..5 = winners of each round.
    columns = [seed_r32()]
    for r in range(5):
        columns.append([m[2] for m in rounds[r]])

    TOTAL = 32
    node_x, node_y, node_text, node_color, hover = [], [], [], [], []
    line_shapes = []

    # Pre-compute y positions per column.
    ys = []
    for c, col in enumerate(columns):
        n = len(col)
        ys.append([(i + 0.5) * TOTAL / n for i in range(n)])

    GREEN, GRAY, IDLE, CHAMP = "#2bd576", "#5b6473", "#aeb6c2", "#ffd54a"

    for c, col in enumerate(columns):
        for i, team in enumerate(col):
            x, y = c, ys[c][i]
            # advanced if this team is the winner of its match in this round
            advanced = False
            if c < 5:
                match_winner = rounds[c][i // 2][2]
                advanced = team is not None and team == match_winner
            if c == 5:
                color = CHAMP
            elif team is None:
                color = IDLE
            elif advanced:
                color = GREEN
            else:
                color = GRAY
            node_x.append(x)
            node_y.append(y)
            node_text.append(label(team) if team else "TBD")
            node_color.append(color)
            hover.append(f"{ROUND_NAMES[c-1] if c>0 else 'Round of 32'} · {label(team)}"
                         if team else "Awaiting pick")

            # connecting line to parent (next column)
            if c < len(columns) - 1:
                px, py = c + 1, ys[c + 1][i // 2]
                line_color = GREEN if (advanced) else "rgba(255,255,255,.08)"
                line_shapes.append(dict(
                    type="line", x0=x, y0=y, x1=px, y1=py,
                    line=dict(color=line_color, width=2 if advanced else 1),
                    layer="below",
                ))

    fig = go.Figure()
    fig.update_layout(shapes=line_shapes)
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        marker=dict(size=13, color=node_color, line=dict(width=0)),
        text=node_text, textposition="middle right",
        textfont=dict(size=11, color="#e6eaf0"),
        hovertext=hover, hoverinfo="text",
    ))

    # Champion crown
    if champion:
        fig.add_annotation(
            x=5, y=ys[5][0] + 1.4, text=f"🏆 {label(champion)}",
            showarrow=False, font=dict(size=16, color=CHAMP), yshift=6,
        )

    for c, name in enumerate(["R32", "R16", "QF", "SF", "Final", "🏆"]):
        fig.add_annotation(x=c, y=TOTAL + 0.6, text=f"<b>{name}</b>",
                           showarrow=False, font=dict(size=13, color="#9aa4b2"))

    fig.update_xaxes(visible=False, range=[-0.3, 5.9])
    fig.update_yaxes(visible=False, range=[-0.5, TOTAL + 2.6 if for_export else TOTAL + 1.8])
    fig.update_layout(
        height=1080, margin=dict(l=10, r=10, t=70 if for_export else 10, b=10),
        showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    if for_export:
        fig.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            title=dict(
                text=f"World Cup 2026 — Champion: {label(champion)} 🏆",
                x=0.5, xanchor="center", font=dict(size=22, color="#2bd576"),
            ),
        )
    return fig


# --------------------------------------------------------------------------- #
#  Pages
# --------------------------------------------------------------------------- #
def page_group_stage():
    st.markdown('<div class="wc-title">Group Stage</div>', unsafe_allow_html=True)
    st.markdown('<div class="wc-sub">Pick the top two from each group. The eight '
                'best third-placed teams advance automatically.</div>',
                unsafe_allow_html=True)
    st.write("")

    group_items = list(GROUPS.items())
    for row in chunks(group_items, 3):
        cols = st.columns(3)
        for col, (g, teams) in zip(cols, row):
            with col, st.container(border=True):
                st.markdown(f"#### Group {g}")
                first = st.radio(
                    "🥇 Winner", teams, key=f"first_{g}",
                    format_func=label,
                )
                rest = [t for t in teams if t != first]
                if st.session_state.get(f"second_{g}") not in rest:
                    st.session_state[f"second_{g}"] = rest[0]
                second = st.radio(
                    "🥈 Runner-up", rest, key=f"second_{g}",
                    format_func=label,
                )
                eliminated = [t for t in teams if t not in (first, second)]
                st.caption("⬇️ " + " · ".join(label(t) for t in eliminated))

    st.write("")
    st.markdown("### 🥉 Best third-placed teams")
    df = third_place_df()
    show = df.copy()
    show["Team"] = show["Team"].map(label)
    show["Status"] = show["Advances"].map({True: "✅ Advances", False: "❌ Out"})
    st.dataframe(
        show[["Group", "Team", "Pts", "Status"]],
        hide_index=True, width="stretch",
    )

    st.write("")
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("🔒 Lock Group Stage", type="primary", width="stretch"):
            st.session_state.locked = True
            autofill(overwrite=False)
            st.session_state._pending_nav = "🏆 Bracket"
            st.rerun()
    with c2:
        if st.session_state.get("locked"):
            st.success("Group stage locked. Head to the **Bracket** page to predict the knockouts.")


def page_bracket():
    st.markdown('<div class="wc-title">Knockout Bracket</div>', unsafe_allow_html=True)
    st.markdown('<div class="wc-sub">Click a team to send it through. '
                'Winners flow left to right all the way to the final.</div>',
                unsafe_allow_html=True)

    top = st.columns([1, 1, 4])
    with top[0]:
        if st.button("🤖 AI Pick (fill all)", width="stretch"):
            autofill(overwrite=True)
            st.rerun()
    with top[1]:
        if st.button("🧹 Reset picks", width="stretch"):
            for k in [k for k in st.session_state if k.startswith("pick_")]:
                del st.session_state[k]
            st.rerun()

    rounds, champion = build_rounds()

    with top[2]:
        if champion:
            st.markdown(
                f"<div style='text-align:right;font-size:1.3rem;font-weight:700;color:#2bd576;'>"
                f"Predicted champion: {label(champion)} 🏆</div>",
                unsafe_allow_html=True,
            )

    tab_pick, tab_viz = st.tabs(["🎯 Make picks", "🌳 Bracket view"])

    with tab_pick:
        cols = st.columns(5)
        for r, col in enumerate(cols):
            with col:
                st.markdown(f"**{ROUND_NAMES[r]}**")
                for i, (a, b, w) in enumerate(rounds[r]):
                    with st.container(border=True):
                        for team in (a, b):
                            disabled = team is None
                            is_win = team is not None and team == w
                            lab = ("✅ " if is_win else "") + label(team)
                            if st.button(
                                lab, key=f"btn_{r}_{i}_{team}",
                                width="stretch", disabled=disabled,
                                type="primary" if is_win else "secondary",
                            ):
                                set_pick(r, i, team)
                                st.rerun()

    with tab_viz:
        st.plotly_chart(bracket_figure(rounds, champion), width="stretch",
                        config={"displayModeBar": False})


def champion_path(rounds, champion):
    """List of (round_name, opponent, winner) for every match the champion played."""
    path = []
    for r in range(5):
        for (a, b, w) in rounds[r]:
            if champion in (a, b) and w == champion:
                opp = b if a == champion else a
                path.append((ROUND_NAMES[r], opp, w))
                break
    return path


def page_prediction():
    st.markdown('<div class="wc-title">My Prediction</div>', unsafe_allow_html=True)
    rounds, champion = build_rounds()

    if not champion:
        st.info("Finish the bracket first — pick winners through to the final, "
                "or hit **AI Pick** on the Bracket page.")
        return

    st.markdown(
        f"""<div class="champ-card">
              <div class="champ-trophy">🏆</div>
              <div style="color:#9aa4b2;text-transform:uppercase;letter-spacing:2px;font-size:.8rem;">
                Your World Cup 2026 Champion</div>
              <div class="champ-name">{label(champion)}</div>
            </div>""",
        unsafe_allow_html=True,
    )
    st.write("")

    path = champion_path(rounds, champion)
    streak = len(path)

    m1, m2, m3 = st.columns(3)
    m1.metric("Consecutive wins", f"{streak}")
    m2.metric("Goals to glory", f"{streak} rounds")
    final_match = rounds[-1][0]
    runner_up = final_match[1] if final_match[0] == champion else final_match[0]
    m3.metric("Beaten in the final", runner_up or "—", label_visibility="visible")

    st.write("")
    st.markdown(f"### {label(champion)}'s road to the title")
    path_df = pd.DataFrame(
        [{"Round": rn, "Opponent": label(opp), "Result": f"{label(champion)} win"}
         for rn, opp, _ in path]
    )
    st.dataframe(path_df, hide_index=True, width="stretch")

    st.markdown("### Every predicted result")
    for r in range(5):
        with st.expander(f"{ROUND_NAMES[r]}  ·  {len(rounds[r])} matches",
                         expanded=(r >= 3)):
            res = pd.DataFrame(
                [{"Match": f"{label(a)}  vs  {label(b)}", "Winner": label(w)}
                 for (a, b, w) in rounds[r]]
            )
            st.dataframe(res, hide_index=True, width="stretch")

    # ----- Visual bracket (the shareable centrepiece) -----
    st.markdown("### 🌳 Your full bracket")
    fig = bracket_figure(rounds, champion)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ----- Share -----
    st.markdown("### 🔗 Share my bracket")
    code = encode_bracket()
    # Keep the address bar in sync so the URL itself is always shareable.
    if st.query_params.get("b") != code:
        st.query_params["b"] = code

    st.markdown("**Share link** — anyone who opens it sees this exact bracket:")
    link_widget = f"""
        <div style="display:flex;gap:8px;font-family:-apple-system,system-ui,sans-serif;">
          <input id="b_link" readonly
                 style="flex:1;padding:9px 11px;border-radius:9px;border:1px solid #2bd57655;
                        background:#0e1117;color:#e6eaf0;font-size:13px;">
          <button id="b_copy"
                  style="padding:9px 16px;border-radius:9px;border:0;background:#2bd576;
                         color:#08130c;font-weight:700;cursor:pointer;font-size:13px;">Copy</button>
        </div>
        <script>
          (function() {{
            var code = {json.dumps(code)};
            var base = "";
            try {{ base = window.parent.location.origin + window.parent.location.pathname; }}
            catch (e) {{ base = ""; }}
            var url = (base || "") + "?b=" + code;
            var inp = document.getElementById("b_link");
            inp.value = url;
            document.getElementById("b_copy").onclick = function() {{
              inp.select(); navigator.clipboard.writeText(url);
              var self = this; self.innerText = "Copied!";
              setTimeout(function() {{ self.innerText = "Copy"; }}, 1500);
            }};
          }})();
        </script>
    """
    try:
        components.html(link_widget, height=56)
    except Exception:
        # Fallback if the components iframe is unavailable: the live URL in the
        # browser address bar already carries ?b=<code>, so this still shares.
        st.code(f"?b={code}", language=None)
    st.caption("Tip: you can also just copy the URL from your browser's address bar — "
               "it always carries your current bracket.")

    st.write("")
    st.markdown("**Download the bracket** to post or send as a file:")
    export_fig = bracket_figure(rounds, champion, for_export=True)
    html = export_fig.to_html(include_plotlyjs="cdn", full_html=True)
    st.download_button(
        "🌐 Download interactive bracket (HTML)", html,
        file_name="wc2026_bracket.html", mime="text/html",
        width="stretch",
    )

    # ----- Copy-paste text summary -----
    st.write("")
    with st.expander("📋 Text summary (copy/paste)"):
        lines = ["🏆 My World Cup 2026 Bracket", ""]
        lines.append(f"CHAMPION: {label(champion)}")
        lines.append(f"Runner-up: {label(runner_up)}")
        lines.append("")
        lines.append("Semi-finalists: " + ", ".join(
            label(w) for (a, b, w) in rounds[2]))
        lines.append("")
        lines.append(f"My champion won {streak} matches in a row to lift the trophy.")
        lines.append("— made with the WC2026 Bracket Predictor")
        st.code("\n".join(lines), language=None)


# --------------------------------------------------------------------------- #
#  App shell
# --------------------------------------------------------------------------- #
def main():
    # A shared bracket arrives as ?b=<code>. Apply it once, before any widget
    # (group radios) is instantiated so the picks take effect this run.
    shared = st.query_params.get("b")
    if shared and st.session_state.get("_applied_share") != shared:
        if apply_bracket(shared):
            st.session_state._applied_share = shared
            st.session_state._seeded = True  # don't overwrite the shared picks

    init_group_state()
    if not st.session_state.get("_seeded"):
        autofill(overwrite=False)   # populated bracket out of the box
        st.session_state._seeded = True

    with st.sidebar:
        st.markdown("## ⚽ WC 2026")
        st.markdown("**Bracket Predictor**")
        st.divider()
        # Apply any navigation requested by a button on the previous run,
        # before the radio widget is instantiated (Streamlit forbids mutating
        # a widget-backed key after the widget exists).
        if "_pending_nav" in st.session_state:
            st.session_state.nav = st.session_state.pop("_pending_nav")
        st.session_state.setdefault("nav", "🏟️ Group Stage")
        nav = st.radio(
            "Pages",
            ["🏟️ Group Stage", "🏆 Bracket", "📋 My Prediction"],
            key="nav", label_visibility="collapsed",
        )
        st.divider()
        _, champ = build_rounds()
        st.caption("Current pick")
        st.markdown(f"### {label(champ) if champ else '—'}")
        st.divider()
        st.caption("48 teams · 12 groups · 31 knockout matches")

    if nav == "🏟️ Group Stage":
        page_group_stage()
    elif nav == "🏆 Bracket":
        page_bracket()
    else:
        page_prediction()


if __name__ == "__main__":
    main()
