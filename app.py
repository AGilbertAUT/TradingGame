
import streamlit as st
import pandas as pd
from datetime import datetime

# ---- CONFIG ----
CONFIG_PATH = "game_config.csv"
SUBMISSIONS_PATH = "submissions.csv"
STOCKS = ["CEN", "FBU", "AIR", "FPH", "WHS"]  # Update if you change tickers in the CSV

# ---- LOAD DATA ----
@st.cache_data
def load_config(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Basic validation
    req_cols = {"round", "headline"} | set(STOCKS)
    missing = req_cols - set(df.columns)
    if missing:
        raise ValueError(f"Config missing columns: {missing}")
    df = df.sort_values("round").reset_index(drop=True)
    return df

def init_state(cfg: pd.DataFrame):
    if "cfg" not in st.session_state:
        st.session_state.cfg = cfg
    if "round_idx" not in st.session_state:
        st.session_state.round_idx = 0
    if "choices" not in st.session_state:
        st.session_state.choices = {}  # round_idx -> {stock: action}
    if "scores" not in st.session_state:
        st.session_state.scores = []  # list of round scores
    if "participant" not in st.session_state:
        st.session_state.participant = ""
    if "locked_rounds" not in st.session_state:
        st.session_state.locked_rounds = set()

def action_to_sign(action: str) -> int:
    return {"Buy": 1, "Sell": -1, "Hold": 0}[action]

def calc_round_score(r_idx: int) -> float:
    cfg_row = st.session_state.cfg.iloc[r_idx]
    choices = st.session_state.choices.get(r_idx, {})
    score = 0.0
    for s in STOCKS:
        action = choices.get(s, "Hold")
        score += action_to_sign(action) * float(cfg_row[s])
    return score

def cum_score() -> float:
    return sum(st.session_state.scores)

def save_submission(r_idx: int, round_score: float):
    cfg_row = st.session_state.cfg.iloc[r_idx]
    ts = datetime.now().isoformat(timespec="seconds")
    data = {
        "timestamp": ts,
        "participant": st.session_state.participant,
        "round": int(cfg_row["round"]),
        "headline": cfg_row["headline"],
        **{f"choice_{s}": st.session_state.choices[r_idx].get(s, "Hold") for s in STOCKS},
        **{f"return_{s}": float(cfg_row[s]) for s in STOCKS},
        "round_score": round_score,
        "cum_score_after": cum_score(),
    }
    try:
        df = pd.read_csv(SUBMISSIONS_PATH)
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    except Exception:
        df = pd.DataFrame([data])
    df.to_csv(SUBMISSIONS_PATH, index=False)

# ---- UI ----
st.set_page_config(page_title="Trading Room Game", page_icon="📈", layout="centered")

st.title("📈 Trading Room Game")
st.caption("Five stocks. Five rounds. Choose **Buy / Sell / Hold** each round and see how you score.")

cfg = load_config(CONFIG_PATH)
init_state(cfg)

with st.sidebar:
    st.header("Controls")
    st.text_input("Participant name", key="participant", placeholder="Type your name (e.g., Team A)")
    if st.button("Reset current player"):
        # Reset decisions and scores but keep participant name
        st.session_state.round_idx = 0
        st.session_state.choices = {}
        st.session_state.scores = []
        st.session_state.locked_rounds = set()
        st.success("Player reset.")
    if st.button("Reset EVERYTHING"):
        for k in ["round_idx", "choices", "scores", "participant", "locked_rounds"]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("All session data cleared.")

    st.markdown("---")
    st.write("**Scoring**: Buy = +return, Sell = −return, Hold = 0")

if not st.session_state.participant:
    st.info("Enter a participant name in the sidebar to get started.")
    st.stop()

rounds_total = len(cfg)
r_idx = st.session_state.round_idx

st.subheader(f"Round {int(cfg.iloc[r_idx]['round'])} of {rounds_total}")
st.markdown(f"**Headline:** {cfg.iloc[r_idx]['headline']}")

locked = r_idx in st.session_state.locked_rounds

cols = st.columns(3)
for i, s in enumerate(STOCKS):
    default = st.session_state.choices.get(r_idx, {}).get(s, "Hold")
    with cols[i % 3]:
        st.selectbox(
            f"{s} action",
            options=["Buy", "Sell", "Hold"],
            index=["Buy", "Sell", "Hold"].index(default),
            disabled=locked,
            key=f"select_{r_idx}_{s}",
        )

# Sync selections into session_state.choices
if not locked:
    st.session_state.choices.setdefault(r_idx, {})
    for s in STOCKS:
        st.session_state.choices[r_idx][s] = st.session_state[f"select_{r_idx}_{s}"]

# Submit / Next
if not locked and st.button("Submit choices for this round", type="primary"):
    round_score = calc_round_score(r_idx)
    st.session_state.scores.append(round_score)
    st.session_state.locked_rounds.add(r_idx)
    save_submission(r_idx, round_score)
    st.success(f"Round {int(cfg.iloc[r_idx]['round'])} submitted! You scored {round_score:+.2f} points.")

# Navigation
nav_cols = st.columns(2)
with nav_cols[0]:
    if r_idx > 0 and st.button("◀ Previous round"):
        st.session_state.round_idx -= 1
with nav_cols[1]:
    if r_idx < rounds_total - 1 and (r_idx in st.session_state.locked_rounds) and st.button("Next round ▶"):
        st.session_state.round_idx += 1

# Scoreboard
st.markdown("---")
st.subheader("Your Performance")
round_scores = pd.Series(st.session_state.scores, name="Round score")
if not round_scores.empty:
    cum_scores = round_scores.cumsum().rename("Cumulative score")
    display = pd.DataFrame({"Round": range(1, len(round_scores) + 1), "Round score": round_scores, "Cumulative score": cum_scores})
    st.dataframe(display, hide_index=True, use_container_width=True)
    st.metric("Cumulative score", f"{cum_scores.iloc[-1]:+.2f}")
else:
    st.info("Submit your first round to see scores.")

# Summary footer
st.caption("© Trading Room Game — Streamlit demo. Edit game_config.csv to customize rounds and returns.")
