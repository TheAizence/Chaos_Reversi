"""
Reversi Ultimate V5  ─  Undo / Hint / Move-Log / Advanced Stats / Piece-Dominance Chart
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random, copy, time, json, os
from datetime import datetime as dt

# ── Optional dependencies ─────────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MPL = True
except ImportError:
    MPL = False

try:
    import numpy as np
    NP = True
except ImportError:
    NP = False

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import pygame
    pygame.mixer.init()
    AUDIO = True
except ImportError:
    AUDIO = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════════════════
CELL_SIZE  = 62
BOARD_SIZE = 0
DIRS = [(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
EMPTY, BLACK, WHITE = 0, 1, 2
CORNERS = [(0,0),(0,7),(7,0),(7,7)]
DATA_FILE    = "reversi_data.json"
MODEL_MEDIUM = "reversi_model_medium.npy"
MODEL_HARD   = "reversi_model_hard.npy"
MAX_HINTS    = 3

# ── Board image grid alignment (measured from tan_board_v2.png @ 496×496) ─────
BOARD_IMG_OX = 13      # pixels from left edge to first grid line
BOARD_IMG_OY = 12      # pixels from top  edge to first grid line
BOARD_IMG_CW = 58.75   # width  of one cell in the scaled image
BOARD_IMG_CH = 58.375  # height of one cell in the scaled image

HMAP = [
    [100,-20,10, 5, 5,10,-20,100],
    [-20,-50,-2,-2,-2,-2,-50,-20],
    [ 10, -2,-1,-1,-1,-1, -2, 10],
    [  5, -2,-1,-1,-1,-1, -2,  5],
    [  5, -2,-1,-1,-1,-1, -2,  5],
    [ 10, -2,-1,-1,-1,-1, -2, 10],
    [-20,-50,-2,-2,-2,-2,-50,-20],
    [100,-20,10, 5, 5,10,-20,100]
]

# ── Achievement Definitions ────────────────────────────────────────────────────
ACHIEVEMENTS = {
    # id : (icon, title, description, rarity)
    "corner_hoarder":    ("🏰", "Corner Hoarder",    "Held all 4 corners in one game",               "Rare"),
    "flawless_victory":  ("💎", "Flawless Victory",  "Won with AI having 0 pieces left",             "Legendary"),
    "speed_demon":       ("⚡", "Speed Demon",        "Won a game in under 60 seconds",               "Rare"),
    "david_vs_goliath":  ("🗡️", "David vs Goliath",  "Beat Hard AI for the first time",              "Legendary"),
    "first_blood":       ("🩸", "First Blood",        "Won your very first game",                     "Common"),
    "veteran":           ("🎖️", "Veteran",            "Played 10 games total",                        "Common"),
    "comeback_king":     ("👑", "Comeback King",      "Won after trailing behind at the halfway mark","Rare"),
    "flip_master":       ("🌀", "Flip Master",        "Flipped 10+ pieces in a single move",          "Rare"),
    "clean_sweep":       ("🧹", "Clean Sweep",        "Finished with 50+ pieces on the board",        "Common"),
    "hard_boiled":       ("🥚", "Hard Boiled",        "Beat Hard AI 3 times",                         "Legendary"),
    "collector":         ("💼", "Collector",          "Unlocked 5 achievements",                      "Common"),
}

# ── The Scholar's Study — Colour Palette (tuned for photo background) ─────────
BG    = "#1A0D06"   # very dark sepia — frame fill (photo shows through canvas)
SURF  = "#201208"   # dark walnut panel
CARD  = "#271608"   # card surface
CARD2 = "#2F1C0A"   # deeper card inset
BDR   = "#6B3E1A"   # antique wood border
ACC   = "#D4AF37"   # tarnished gold (primary accent — brass plate)
ACC2  = "#B8860B"   # dark goldenrod (secondary)
NEON  = "#C8A45A"   # parchment amber (hint dots)
SUCC  = "#6BAF6B"   # aged olive-green (win / success)
DANG  = "#B84040"   # burgundy-red (danger / loss)
WARN  = "#D4AF37"   # gold warning
TXT   = "#F5F0DC"   # aged parchment / ivory
TXT2  = "#9A7B5A"   # faded ink
HINT_COL  = "#D4AF37"
BOARD_BG  = "#4A2E14"   # mahogany board base (fallback)
BOARD_LN  = "#2E150B"   # dark walnut grid lines

# ── Piece colours (used in _draw) ─────────────────────────────────────────────
PIECE_BLACK_FILL    = "#1A0A00"   # ebony — near-black warm
PIECE_BLACK_OUTLINE = "#5C3D1E"   # dark wood ring
PIECE_WHITE_FILL    = "#F8F0DC"   # ivory / bone
PIECE_WHITE_OUTLINE = "#C8A882"   # antique ivory rim

# ── Fonts — The Scholar's Study ───────────────────────────────────────────────
F_LOGO  = ("Palatino Linotype", 36, "bold italic")
F_TITLE = ("Georgia",           18, "bold")
F_HEAD  = ("Georgia",           13, "bold")
F_BTN   = ("Georgia",           11, "bold")
F_BODY  = ("Georgia",           11)
F_SMALL = ("Helvetica",          9)
F_MONO  = ("Georgia",           11)


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════
def _shade(col: str, f: float) -> str:
    c = col.lstrip("#")
    r, g, b = int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)
    return f"#{min(255,int(r*f)):02x}{min(255,int(g*f)):02x}{min(255,int(b*f)):02x}"


def mkbtn(parent, text, cmd, bg=ACC, fg=TXT, padx=18, pady=9, font=None, width=None):
    f   = font or F_BTN
    hv  = _shade(bg, 1.18)   # brighter on hover (like light catching metal)
    pr  = _shade(bg, 0.72)   # pressed darker shade
    b   = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                    activebackground=pr, activeforeground=fg,
                    relief=tk.RAISED, bd=3, padx=padx, pady=pady,
                    font=f, cursor="hand2", highlightthickness=0)
    if width is not None:
        b.config(width=width)
    b.bind("<Enter>",         lambda e: b.config(bg=hv, relief=tk.RAISED))
    b.bind("<Leave>",         lambda e: b.config(bg=bg,  relief=tk.RAISED))
    b.bind("<ButtonPress-1>", lambda e: b.config(bg=pr,  relief=tk.SUNKEN))
    b.bind("<ButtonRelease-1>",lambda e:b.config(bg=hv,  relief=tk.RAISED))
    return b


def sep(parent, orient="h", color=BDR, thick=1, padx=0, pady=4):
    if orient == "h":
        tk.Frame(parent, bg=color, height=thick).pack(fill=tk.X, padx=padx, pady=pady)
    else:
        tk.Frame(parent, bg=color, width=thick).pack(fill=tk.Y, padx=padx, pady=pady)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MANAGER  ─ extended with diff-win-rate / corner-control / highest-flip
# ═══════════════════════════════════════════════════════════════════════════════
class DataManager:
    # Base template – used for new player entries AND for migration of old ones
    _DS = {
        "played": 0, "wins": 0, "losses": 0, "ties": 0,
        "high_score": 0, "total_time": 0,
        # ── NEW v5 fields ────────────────────────────────────────────
        "diff_stats": {
            "Easy":   {"played": 0, "wins": 0},
            "Medium": {"played": 0, "wins": 0},
            "Hard":   {"played": 0, "wins": 0},
        },
        "total_corners": 0,
        "corner_games":  0,
        "highest_flip":  0,
        "achievements":  [],   # list of unlocked achievement ids
        "current_streak": 0,   # consecutive win streak
        "best_streak":    0,   # all-time best win streak
        "daily_games":    {},  # "YYYY-MM-DD" -> {"played":n,"wins":n}
    }

    @classmethod
    def _new_ps(cls):
        """Return a deep-copied fresh player-stats dict."""
        return copy.deepcopy(cls._DS)

    @classmethod
    def _migrate(cls, ps: dict) -> dict:
        """Ensure older saved dicts have all v5 keys."""
        for key, val in cls._DS.items():
            if key not in ps:
                ps[key] = copy.deepcopy(val)
        if "diff_stats" in ps:
            for d in ("Easy", "Medium", "Hard"):
                ps["diff_stats"].setdefault(d, {"played": 0, "wins": 0})
        return ps

    def __init__(self):
        self.data = {"leaderboard": [], "player_stats": {}, "stats": self._new_ps()}
        self._load()

    def _load(self):
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE) as f:
                d = json.load(f)
            self.data["leaderboard"]  = d.get("leaderboard", [])
            raw_ps = d.get("player_stats", {})
            self.data["player_stats"] = {
                name: self._migrate(ps) for name, ps in raw_ps.items()
            }
            self.data["stats"] = self._migrate(d.get("stats", self._new_ps()))
        except Exception:
            pass

    def save(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def unique_names(self):
        names = set(e["name"] for e in self.data["leaderboard"])
        names |= set(self.data["player_stats"].keys())
        return sorted(names)

    # corners  = number of board corners held by BLACK at game end (0-4)
    # best_flip = highest single-move flip count by the player this game
    def add_entry(self, name, b_cnt, time_str, diff, mode, result, score,
                  corners: int = 0, best_flip: int = 0):
        RMAP = {"win": "wins", "loss": "losses", "tie": "ties"}
        self.data["leaderboard"].append({
            "name": name, "score": score, "pieces": b_cnt,
            "time": time_str, "diff": diff, "mode": mode,
            "result": result, "corners": corners,
            "best_flip": best_flip, "ts": int(time.time())
        })
        self.data["leaderboard"].sort(key=lambda x: (-x["score"], x["time"]))

        # ── Player stats ──────────────────────────────────────────────────────
        ps = self.data["player_stats"].setdefault(name, self._new_ps())
        self._migrate(ps)
        ps["played"] += 1
        ps[RMAP.get(result, "losses")] += 1
        if score > ps["high_score"]:
            ps["high_score"] = score

        # Diff-specific win rate
        if diff in ps["diff_stats"]:
            ps["diff_stats"][diff]["played"] += 1
            if result == "win":
                ps["diff_stats"][diff]["wins"] += 1

        # Corner control
        ps["total_corners"] += corners
        ps["corner_games"]  += 1

        # Highest flip combo
        if best_flip > ps["highest_flip"]:
            ps["highest_flip"] = best_flip

        # ── Streak tracking ───────────────────────────────────────────────────
        import datetime as _dt
        today = _dt.date.today().isoformat()
        if result == "win":
            ps["current_streak"] = ps.get("current_streak", 0) + 1
            if ps["current_streak"] > ps.get("best_streak", 0):
                ps["best_streak"] = ps["current_streak"]
        elif result == "loss":
            ps["current_streak"] = 0
        # ties don't break or extend the streak

        # ── Daily activity grid ───────────────────────────────────────────────
        day = ps.setdefault("daily_games", {}).setdefault(
            today, {"played": 0, "wins": 0})
        day["played"] += 1
        if result == "win":
            day["wins"] += 1

        # ── Global stats ──────────────────────────────────────────────────────
        gs = self.data["stats"]
        self._migrate(gs)
        gs["played"] += 1
        gs[RMAP.get(result, "losses")] += 1
        if score > gs["high_score"]:
            gs["high_score"] = score

        self.save()

    def get_leaderboard(self, diff="All", mode="All", name=""):
        out = []
        for e in self.data["leaderboard"]:
            if diff != "All" and e.get("diff") != diff:
                continue
            if mode != "All" and e.get("mode") != mode:
                continue
            if name and name.lower() not in e["name"].lower():
                continue
            out.append(e)
        return out

    def player_stats(self, name):
        return self.data["player_stats"].get(name)

    # ── Achievement helpers ───────────────────────────────────────────────────
    def get_achievements(self, name: str) -> list:
        ps = self.data["player_stats"].get(name)
        if not ps:
            return []
        return ps.get("achievements", [])

    def unlock_achievement(self, name: str, ach_id: str) -> bool:
        """Unlock achievement for player. Returns True if newly unlocked."""
        ps = self.data["player_stats"].setdefault(name, self._new_ps())
        self._migrate(ps)
        if "achievements" not in ps:
            ps["achievements"] = []
        if ach_id in ps["achievements"]:
            return False
        ps["achievements"].append(ach_id)
        self.save()
        return True

    def evaluate_achievements(self, name: str, result: str, diff: str,
                              rt_secs: int, bc: int, wc: int,
                              corners: int, best_flip: int,
                              piece_track: list) -> list:
        """Check all conditions and return list of newly-unlocked achievement ids."""
        ps  = self.data["player_stats"].get(name)
        if not ps:
            return []
        new_ach = []

        def _try(aid):
            if self.unlock_achievement(name, aid):
                new_ach.append(aid)

        # first_blood – first ever win
        if result == "win" and ps.get("wins", 0) <= 1:
            _try("first_blood")

        # veteran – 10 games played
        if ps.get("played", 0) >= 10:
            _try("veteran")

        # speed_demon – win in < 60 s
        if result == "win" and rt_secs < 60:
            _try("speed_demon")

        # flawless_victory – win with AI having 0 pieces
        if result == "win" and wc == 0:
            _try("flawless_victory")

        # corner_hoarder – held all 4 corners
        if corners == 4:
            _try("corner_hoarder")

        # flip_master – flipped 10+ in one move
        if best_flip >= 10:
            _try("flip_master")

        # clean_sweep – finished with 50+ pieces
        if result == "win" and bc >= 50:
            _try("clean_sweep")

        # david_vs_goliath – beat Hard AI
        if result == "win" and diff == "Hard":
            _try("david_vs_goliath")

        # hard_boiled – beat Hard AI 3 times
        ds = ps.get("diff_stats", {}).get("Hard", {})
        if ds.get("wins", 0) >= 3:
            _try("hard_boiled")

        # comeback_king – was trailing at halfway then won
        if result == "win" and piece_track:
            mid = len(piece_track) // 2
            if mid > 0:
                _, mb, mw = piece_track[mid]
                if mb < mw:          # trailing at midpoint
                    _try("comeback_king")

        # collector – 5 achievements unlocked
        if len(ps.get("achievements", [])) >= 5:
            _try("collector")

        return new_ach


# ═══════════════════════════════════════════════════════════════════════════════
# NEURAL MODEL WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════
class NeuralModel:
    def __init__(self, path):
        self.ok = False
        self.W, self.b = [], []
        if not NP or not os.path.exists(path):
            return
        try:
            d = np.load(path, allow_pickle=True).item()
            self.W = d["weights"]
            self.b = d["biases"]
            self.ok = True
        except Exception as e:
            print(f"[NeuralModel] {path}: {e}")

    @staticmethod
    def features(board, vw, vb):
        f = np.zeros(150, dtype=np.float32)
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] == WHITE:
                    f[r*8+c] = 1.0
                elif board[r][c] == BLACK:
                    f[r*8+c] = -1.0
        f[64] = len(vw) / 30.0
        f[65] = len(vb) / 30.0
        for i, (r, c) in enumerate([(0,0),(0,BOARD_SIZE - 1),(BOARD_SIZE - 1,0),(BOARD_SIZE - 1, BOARD_SIZE - 1)]):
            if board[r][c] == WHITE:
                f[66+i] = 1.0
            elif board[r][c] == BLACK:
                f[66+i] = -1.0
        return f

    def evaluate(self, board, vw, vb):
        if not self.ok:
            return None
        x = self.features(board, vw, vb)
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            x = x @ W + b
            if i < len(self.W) - 1:
                x = np.maximum(0, x)
        return float(np.tanh(x)[0])


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED GAME LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def valid_moves(board, player):
    opp   = WHITE if player == BLACK else BLACK
    moves = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] not in (EMPTY, None):
                continue
            for dr, dc in DIRS:
                nr, nc = r+dr, c+dc
                found = False
                while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == opp:
                    nr += dr; nc += dc; found = True
                if found and 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == player:
                    moves.append((r, c)); break
    return moves


def apply_move(board, player, r, c):
    board[r][c] = player
    opp     = WHITE if player == BLACK else BLACK
    flipped = []
    for dr, dc in DIRS:
        nr, nc   = r+dr, c+dc
        to_flip  = []
        while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == opp:
            to_flip.append((nr, nc)); nr += dr; nc += dc
        if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == player:
            for fr, fc in to_flip:
                board[fr][fc] = player
                flipped.append((fr, fc))
    return flipped


def heuristic(board):
    s = 0
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == WHITE:
                s += HMAP[r][c]
            elif board[r][c] == BLACK:
                s -= HMAP[r][c]
    return s


def minimax(board, depth, alpha, beta, is_max, model=None):
    player = WHITE if is_max else BLACK
    moves  = valid_moves(board, player)
    if depth == 0 or not moves:
        if model and model.ok:
            vw  = valid_moves(board, WHITE)
            vb  = valid_moves(board, BLACK)
            val = model.evaluate(board, vw, vb)
            if val is not None:
                return val * 800, None
        return heuristic(board), None

    best_m = None
    if is_max:
        mx = float("-inf")
        for r, c in moves:
            tb = copy.deepcopy(board)
            apply_move(tb, WHITE, r, c)
            ev, _ = minimax(tb, depth-1, alpha, beta, False, model)
            if ev > mx:
                mx, best_m = ev, (r, c)
            alpha = max(alpha, ev)
            if beta <= alpha:
                break
        return mx, best_m
    else:
        mn = float("inf")
        for r, c in moves:
            tb = copy.deepcopy(board)
            apply_move(tb, BLACK, r, c)
            ev, _ = minimax(tb, depth-1, alpha, beta, True, model)
            if ev < mn:
                mn, best_m = ev, (r, c)
            beta = min(beta, ev)
            if beta <= alpha:
                break
        return mn, best_m


# ─── Helper: compute best move for BLACK using AI logic ───────────────────────
def best_move_for_black(app, board):
    """Return the best (r,c) for BLACK using the same logic as the AI (minimax depth-2)."""
    moves = valid_moves(board, BLACK)
    if not moves:
        return None
    model = app.ml_med if app.ml_med.ok else None
    _, best = minimax(board, 2, float("-inf"), float("inf"), False, model)
    return best if best else moves[0]


# ── AI Taunt & Commentary Library ─────────────────────────────────────────────
_TAUNTS = {
    "corner_grab": [
        "Corners are MINE now. 😏",
        "That's a corner. Game over? 🏰",
        "Cornerstone secured. Classic.",
        "Love this corner. Thanks! 🙃",
    ],
    "big_flip": [
        "Ooh, {n} flips at once. Bold move!",
        "Did that sting? {n} of yours are mine 😈",
        "That's {n} flips in one go. Impressive... for me.",
        "Combo! {n} pieces flipped. 🎯",
    ],
    "player_corner": [
        "Nice corner grab! Don't get used to it.",
        "Okay, respect. That corner is yours... for now.",
        "Sneaky corner play. I see you. 👀",
        "You got a corner. Congrats, I guess.",
    ],
    "player_big_flip": [
        "Oops, that was bold. Well played.",
        "I did NOT see that coming. 😤",
        "Okay that flip was actually good.",
        "Fine. {n} flips. I'll allow it.",
    ],
    "ai_losing": [
        "I'm... recalculating. 🤔",
        "This isn't over. I'm just warming up.",
        "Lucky moves won't save you forever.",
        "Hmm. Interesting. Very interesting.",
    ],
    "ai_winning": [
        "Resistance is futile. 🤖",
        "You're doing great... for a human.",
        "The board is mine. Accept your fate.",
        "I could end this now. But where's the fun?",
    ],
    "few_moves_left": [
        "We're almost done here.",
        "Endgame. Choose wisely.",
        "The board is filling up… 🧩",
        "Last few moves. Make them count.",
    ],
    "player_slow": [
        "Still thinking? Take your time… ⏳",
        "I've computed 10,000 positions while you waited.",
        "The board isn't going anywhere.",
        "No rush. I'll just be here. Thinking.",
    ],
    "game_start": [
        "Let's see what you've got.",
        "I've been waiting. Ready when you are.",
        "Another challenger. How delightful.",
        "Shall we? 🤝",
    ],
}

def _pick_taunt(key: str, **fmt) -> str:
    msgs = _TAUNTS.get(key, [])
    if not msgs:
        return ""
    t = random.choice(msgs)
    try:
        return t.format(**fmt)
    except Exception:
        return t


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION ROOT
# ═══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Reversi — The Scholar's Study")
        self.geometry("1000x720")
        self.minsize(860, 600)
        self.configure(bg=BG)

        self.dm         = DataManager()
        self.ml_med     = NeuralModel(MODEL_MEDIUM)
        self.ml_hard    = NeuralModel(MODEL_HARD)
        self.player     = tk.StringVar(value="Player")
        self.game_mode  = tk.StringVar(value="Standard")
        self.difficulty = tk.StringVar(value="Medium")
        self.is_muted   = False
        self.images     = {}
        self.sfx        = {}
        self._fs        = False
        self.show_hints = True
        self.chaos_manager = None

        # ── Background image system ────────────────────────────────────────────
        self._bg_raw    = None     # PIL Image loaded once at startup
        self._bg_photo  = None     # cached PhotoImage — reused until size changes
        self._bg_size   = (0, 0)   # (W, H) of current cached photo
        self._resize_job = None    # debounce handle
        self._load_bg_raw()        # load PIL image (no rendering yet)

        self._load_assets()
        self._apply_ttk_style()
        self._build_screens()
        self.bind("<F11>",      lambda e: self._toggle_fs())
        self.bind("<Escape>",   lambda e: self.attributes("-fullscreen", False))
        self.bind("<Configure>",self._on_resize_debounce)
        self.show("start")
        # Render background after layout settles
        self.after(150, self._update_bg_now)

    # ── Background: load raw PIL image once ────────────────────────────────────
    def _load_bg_raw(self):
        if not PIL_OK:
            return
        d    = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(d, "bg_scholar.png")
        if not os.path.exists(path):
            print(f"[bg] bg_scholar.png not found in {d}")
            return
        try:
            self._bg_raw = Image.open(path).convert("RGB")
            print(f"[bg] loaded {path}  {self._bg_raw.size}")
        except Exception as e:
            print(f"[bg] load error: {e}")

    # ── Background: render / cache at current window size ─────────────────────
    def _get_bg_photo(self, W, H):
        """
        Return a PhotoImage of the background sized to (W, H).
        Result is cached — only re-rendered when the size changes.
        """
        if W < 2 or H < 2:
            return None
        if self._bg_raw is None:
            return None
        if (W, H) == self._bg_size and self._bg_photo is not None:
            return self._bg_photo   # cache hit — no PIL work needed

        try:
            iw, ih = self._bg_raw.size
            scale  = max(W / iw, H / ih)
            nw, nh = int(iw * scale), int(ih * scale)
            img    = self._bg_raw.resize((nw, nh), Image.Resampling.BILINEAR)  # faster than LANCZOS
            x0     = (nw - W) // 2
            y0     = (nh - H) // 2
            img    = img.crop((x0, y0, x0 + W, y0 + H))

            # Single dark overlay blend — no expensive loop
            overlay = Image.new("RGB", (W, H), (22, 12, 4))
            img     = Image.blend(img, overlay, alpha=0.50)

            self._bg_photo = ImageTk.PhotoImage(img)
            self._bg_size  = (W, H)
        except Exception as e:
            print(f"[bg] render error: {e}")
            return None

        return self._bg_photo

    # ── Debounced resize handler — fires at most once per 250 ms ──────────────
    def _on_resize_debounce(self, _e=None):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(250, self._update_bg_now)

    def _update_bg_now(self):
        """Re-render the background at the current window size and push to all screens."""
        self._resize_job = None
        W = self.winfo_width()
        H = self.winfo_height()
        photo = self._get_bg_photo(W, H)
        if not photo:
            return
        for scr in self._screens.values():
            if hasattr(scr, "_bg_lbl"):
                scr._bg_lbl.config(image=photo)
                scr._bg_lbl._ref = photo   # prevent GC

    # ── Assets ────────────────────────────────────────────────────────────────
    def _load_assets(self):
        d = os.path.dirname(os.path.abspath(__file__))
        IMG_MAP = [
            ("win",  ["image_1.gif", "image_1.png", "image_1.jpg"]),
            ("loss", ["image_0.jpg", "image_0.png", "image_0.gif"]),
            ("tie",  ["image_2.jpg", "image_2.png", "image_2.gif"]),
        ]
        IMG_SIZE = (240, 160)
        for key, fnames in IMG_MAP:
            for fn in fnames:
                p = os.path.join(d, fn)
                if not os.path.exists(p):
                    continue
                ext = fn.rsplit(".", 1)[-1].lower()
                try:
                    if PIL_OK:
                        raw = Image.open(p)
                        if ext == "gif":
                            frames = []
                            try:
                                fi = 0
                                while True:
                                    raw.seek(fi)
                                    frame = raw.convert("RGBA").resize(IMG_SIZE, Image.Resampling.LANCZOS)
                                    frames.append(ImageTk.PhotoImage(frame))
                                    fi += 1
                            except EOFError:
                                pass
                            if frames:
                                self.images[key]             = frames[0]
                                self.images[f"{key}_frames"] = frames
                                break
                        else:
                            img = raw.convert("RGB").resize(IMG_SIZE, Image.Resampling.LANCZOS)
                            self.images[key] = ImageTk.PhotoImage(img)
                            break
                    elif ext in ("gif", "png"):
                        frames = []
                        if ext == "gif":
                            i = 0
                            while True:
                                try:
                                    frames.append(tk.PhotoImage(file=p, format=f"gif -index {i}"))
                                    i += 1
                                except tk.TclError:
                                    break
                        else:
                            frames.append(tk.PhotoImage(file=p))
                        if frames:
                            self.images[key]             = frames[0]
                            self.images[f"{key}_frames"] = frames
                            break
                except Exception as e:
                    print(f"[assets] ✘ {fn}: {e}")
                    continue
        if AUDIO:
            bgm = os.path.join(d, "Background_music.mp3")
            if os.path.exists(bgm):
                try:
                    pygame.mixer.music.load(bgm)
                    pygame.mixer.music.set_volume(0.3)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            for key, fn in [("win","win.wav"),("loss","lose.wav"),("tie","tie.wav")]:
                p = os.path.join(d, fn)
                if os.path.exists(p):
                    try:
                        self.sfx[key] = pygame.mixer.Sound(p)
                    except Exception:
                        pass

    def play_sfx(self, key):
        if AUDIO and not self.is_muted and key in self.sfx:
            pygame.mixer.music.set_volume(0.05)
            self.sfx[key].set_volume(1.0)
            self.sfx[key].play()
            self.after(3500, lambda: pygame.mixer.music.set_volume(0.3)
                       if not self.is_muted else None)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if AUDIO:
            pygame.mixer.music.set_volume(0 if self.is_muted else 0.3)

    # ── TTK styling ───────────────────────────────────────────────────────────
    def _apply_ttk_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        for widget in ("TCombobox", "TEntry"):
            s.configure(widget, fieldbackground=CARD2, background=CARD2,
                        foreground=TXT, arrowcolor=TXT2, insertcolor=TXT,
                        selectbackground=ACC2, selectforeground=BG,
                        bordercolor=BDR, lightcolor=CARD2, darkcolor=CARD2)
            s.map(widget, fieldbackground=[("readonly", CARD2)],
                  selectbackground=[("readonly", ACC2)])
        s.configure("Treeview",
                    background=CARD, foreground=TXT, fieldbackground=CARD,
                    rowheight=28, font=F_BODY)
        s.configure("Treeview.Heading",
                    background=CARD2, foreground=ACC,
                    font=("Georgia", 10, "bold"), relief="raised")
        s.map("Treeview", background=[("selected", ACC2)],
              foreground=[("selected", BG)])
        s.configure("Vertical.TScrollbar",
                    background=CARD2, troughcolor=SURF,
                    bordercolor=BDR, arrowcolor=TXT2)

    # ── Screen management ─────────────────────────────────────────────────────
    def _build_screens(self):
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill=tk.BOTH, expand=True)
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)
        self._screens = {}
        for name, Cls in [
            ("start",        StartScreen),
            ("mode",         ModeScreen),
            ("difficulty",   DifficultyScreen),
            ("game",         GameScreen),
            ("spectator",    SpectatorScreen),
            ("leaderboard",  LeaderboardFullScreen),
            ("activity",     ActivityScreen),
            ("achievements", AchievementsScreen),
            ("postgame",     PostGameScreen),
        ]:
            scr = Cls(self._container, self)
            scr.grid(row=0, column=0, sticky="nsew")

            # ── Inject background label into every screen ──────────────────────
            # It's placed at (0,0) filling the entire frame, then lowered behind
            # all other widgets. This is the only reliable way in tkinter to show
            # a photo background through opaque Frame widgets.
            bg_lbl = tk.Label(scr, bg=BG, bd=0, highlightthickness=0)
            bg_lbl.place(x=0, y=0, relwidth=1, relheight=1)
            bg_lbl.lower()          # push to bottom of z-stack
            scr._bg_lbl = bg_lbl   # keep reference
            self._screens[name] = scr

    def show(self, name, **kw):
        s = self._screens[name]
        s.tkraise()
        # Ensure the bg label is still at the bottom after tkraise
        if hasattr(s, "_bg_lbl"):
            s._bg_lbl.lower()
        if hasattr(s, "on_show"):
            s.on_show(**kw)

    def _toggle_fs(self):
        self._fs = not self._fs
        self.attributes("-fullscreen", self._fs)

    # ── Assets ────────────────────────────────────────────────────────────────
    def _load_assets(self):
        d = os.path.dirname(os.path.abspath(__file__))
        IMG_MAP = [
            ("win",  ["image_1.gif", "image_1.png", "image_1.jpg"]),
            ("loss", ["image_0.jpg", "image_0.png", "image_0.gif"]),
            ("tie",  ["image_2.jpg", "image_2.png", "image_2.gif"]),
        ]
        IMG_SIZE = (240, 160)
        for key, fnames in IMG_MAP:
            for fn in fnames:
                p = os.path.join(d, fn)
                if not os.path.exists(p):
                    continue
                ext = fn.rsplit(".", 1)[-1].lower()
                try:
                    if PIL_OK:
                        raw = Image.open(p)
                        if ext == "gif":
                            frames = []
                            try:
                                fi = 0
                                while True:
                                    raw.seek(fi)
                                    frame = raw.convert("RGBA").resize(IMG_SIZE, Image.Resampling.LANCZOS)
                                    frames.append(ImageTk.PhotoImage(frame))
                                    fi += 1
                            except EOFError:
                                pass
                            if frames:
                                self.images[key]             = frames[0]
                                self.images[f"{key}_frames"] = frames
                                break
                        else:
                            img = raw.convert("RGB").resize(IMG_SIZE, Image.Resampling.LANCZOS)
                            self.images[key] = ImageTk.PhotoImage(img)
                            break
                    elif ext in ("gif", "png"):
                        frames = []
                        if ext == "gif":
                            i = 0
                            while True:
                                try:
                                    frames.append(tk.PhotoImage(file=p, format=f"gif -index {i}"))
                                    i += 1
                                except tk.TclError:
                                    break
                        else:
                            frames.append(tk.PhotoImage(file=p))
                        if frames:
                            self.images[key]             = frames[0]
                            self.images[f"{key}_frames"] = frames
                            break
                except Exception as e:
                    print(f"[assets] ✘ {fn}: {e}")
                    continue
        if AUDIO:
            bgm = os.path.join(d, "Background_music.mp3")
            if os.path.exists(bgm):
                try:
                    pygame.mixer.music.load(bgm)
                    pygame.mixer.music.set_volume(0.3)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            for key, fn in [("win","win.wav"),("loss","lose.wav"),("tie","tie.wav")]:
                p = os.path.join(d, fn)
                if os.path.exists(p):
                    try:
                        self.sfx[key] = pygame.mixer.Sound(p)
                    except Exception:
                        pass

    def play_sfx(self, key):
        if AUDIO and not self.is_muted and key in self.sfx:
            pygame.mixer.music.set_volume(0.05)
            self.sfx[key].set_volume(1.0)
            self.sfx[key].play()
            self.after(3500, lambda: pygame.mixer.music.set_volume(0.3)
                       if not self.is_muted else None)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if AUDIO:
            pygame.mixer.music.set_volume(0 if self.is_muted else 0.3)

    # ── TTK styling ───────────────────────────────────────────────────────────
    def _apply_ttk_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        for widget in ("TCombobox", "TEntry"):
            s.configure(widget, fieldbackground=CARD2, background=CARD2,
                        foreground=TXT, arrowcolor=TXT2, insertcolor=TXT,
                        selectbackground=ACC2, selectforeground=BG,
                        bordercolor=BDR, lightcolor=CARD2, darkcolor=CARD2)
            s.map(widget, fieldbackground=[("readonly", CARD2)],
                  selectbackground=[("readonly", ACC2)])
        s.configure("Treeview",
                    background=CARD, foreground=TXT, fieldbackground=CARD,
                    rowheight=28, font=F_BODY)
        s.configure("Treeview.Heading",
                    background=CARD2, foreground=ACC,
                    font=("Georgia", 10, "bold"), relief="raised")
        s.map("Treeview", background=[("selected", ACC2)],
              foreground=[("selected", BG)])
        s.configure("Vertical.TScrollbar",
                    background=CARD2, troughcolor=SURF,
                    bordercolor=BDR, arrowcolor=TXT2)

    # ── Screen management ─────────────────────────────────────────────────────
    def _build_screens(self):
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill=tk.BOTH, expand=True)
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)
        self._screens = {}
        for name, Cls in [
            ("start",        StartScreen),
            ("mode",         ModeScreen),
            ("difficulty",   DifficultyScreen),
            ("game",         GameScreen),
            ("spectator",    SpectatorScreen),
            ("leaderboard",  LeaderboardFullScreen),
            ("activity",     ActivityScreen),
            ("achievements", AchievementsScreen),
            ("postgame",     PostGameScreen),
        ]:
            scr = Cls(self._container, self)
            scr.grid(row=0, column=0, sticky="nsew")
            self._screens[name] = scr

    def show(self, name, **kw):
        s = self._screens[name]
        s.tkraise()
        if hasattr(s, "on_show"):
            s.on_show(**kw)

    def _toggle_fs(self):
        self._fs = not self._fs
        self.attributes("-fullscreen", self._fs)





# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 ─ START / LOBBY
# ═══════════════════════════════════════════════════════════════════════════════
class StartScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        # ── Left 52% panel ────────────────────────────────────────────────────
        left = tk.Frame(self, bg=BG)
        left.place(relx=0, rely=0, relwidth=0.52, relheight=1)

        logo_wrap = tk.Frame(left, bg=BG)
        logo_wrap.pack(pady=(28, 0))
        tk.Label(logo_wrap, text="Reversi", font=F_LOGO, bg=BG, fg=ACC).pack()
        tk.Label(logo_wrap, text="✦  T H E   S C H O L A R ' S   S T U D Y  ✦",
                 font=("Georgia", 10, "italic"), bg=BG, fg=NEON).pack()

        sep(left, padx=30, pady=8)

        # ── Player card ───────────────────────────────────────────────────────
        pc = tk.Frame(left, bg=CARD, pady=16, padx=28)
        pc.pack(padx=32, fill=tk.X)
        tk.Label(pc, text="▸ SELECT PLAYER", font=F_HEAD, bg=CARD, fg=NEON).pack(anchor="w")
        tk.Label(pc, text="Type new name or pick an existing player:",
                 font=F_SMALL, bg=CARD, fg=TXT2).pack(anchor="w", pady=(4, 2))
        self.combo = ttk.Combobox(pc, textvariable=self.app.player, font=F_BODY, width=26)
        self.combo.pack(fill=tk.X, pady=(4, 10))
        mkbtn(pc, "▶  START GAME", self._go_mode, bg=ACC, padx=0, pady=11).pack(fill=tk.X)

        sep(left, padx=32, pady=6)

        # ── Recent Players card ───────────────────────────────────────────────
        rp = tk.Frame(left, bg=CARD, pady=12, padx=24)
        rp.pack(padx=32, fill=tk.X)
        rp_hdr = tk.Frame(rp, bg=CARD)
        rp_hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(rp_hdr, text="▸ RECENT PLAYERS", font=F_HEAD, bg=CARD, fg=NEON).pack(side=tk.LEFT)
        mkbtn(rp_hdr, "🏆 Trophies", lambda: self.app.show("achievements"),
              bg=CARD2, fg=WARN, padx=8, pady=4, font=F_SMALL).pack(side=tk.RIGHT, padx=(4,0))
        mkbtn(rp_hdr, "📅 Activity", lambda: self.app.show("activity"),
              bg=CARD2, fg=NEON, padx=8, pady=4, font=F_SMALL).pack(side=tk.RIGHT, padx=(4,0))
        mkbtn(rp_hdr, "📊 Leaderboard", lambda: self.app.show("leaderboard"),
              bg=ACC2, fg=TXT, padx=10, pady=4, font=F_SMALL).pack(side=tk.RIGHT)

        pl_canvas = tk.Canvas(rp, bg=CARD, height=130, highlightthickness=0, bd=0)
        pl_canvas.pack(fill=tk.X, side=tk.LEFT, expand=True)
        pl_sb = ttk.Scrollbar(rp, orient="vertical", command=pl_canvas.yview)
        pl_canvas.configure(yscrollcommand=pl_sb.set)
        self._players_frame = tk.Frame(pl_canvas, bg=CARD)
        _pw = pl_canvas.create_window((0, 0), window=self._players_frame, anchor="nw")

        def _on_pf_conf(e):
            pl_canvas.configure(scrollregion=pl_canvas.bbox("all"))
        def _on_pc_conf(e):
            pl_canvas.itemconfig(_pw, width=e.width)
        def _mw(e):
            pl_canvas.yview_scroll(int(-1*(e.delta/120)), "units")

        self._players_frame.bind("<Configure>", _on_pf_conf)
        pl_canvas.bind("<Configure>", _on_pc_conf)
        pl_canvas.bind("<MouseWheel>", _mw)
        self._players_frame.bind("<MouseWheel>", _mw)

        sep(left, padx=32, pady=6)

        # ── Your stats mini-card ──────────────────────────────────────────────
        sc = tk.Frame(left, bg=CARD2, pady=12, padx=28)
        sc.pack(padx=32, fill=tk.X)
        tk.Label(sc, text="YOUR STATS", font=("Georgia", 9, "bold"),
                 bg=CARD2, fg=TXT2).pack(anchor="w")
        self._slbl = tk.Label(sc, text="─  No data yet", font=F_BODY,
                              bg=CARD2, fg=TXT, justify=tk.LEFT)
        self._slbl.pack(anchor="w", pady=(4, 0))

        # ── Bottom bar ────────────────────────────────────────────────────────
        bot = tk.Frame(left, bg=BG)
        bot.pack(side=tk.BOTTOM, pady=14, fill=tk.X, padx=32)
        mkbtn(bot, "🔇 Music", self.app.toggle_mute,
              bg=CARD2, fg=TXT2, padx=12, pady=7, font=F_SMALL).pack(side=tk.RIGHT)
        mkbtn(bot, "🤖 Watch AI vs AI", lambda: self.app.show("spectator"),
              bg=CARD2, fg=NEON, padx=12, pady=7, font=F_SMALL).pack(side=tk.LEFT)

        self.combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_stats())
        self.combo.bind("<KeyRelease>",          lambda e: self._refresh_stats())

        # ── Right 48% panel ─── Leaderboard ───────────────────────────────────
        right = tk.Frame(self, bg=SURF)
        right.place(relx=0.52, rely=0, relwidth=0.48, relheight=1)

        hdr = tk.Frame(right, bg=SURF, pady=16)
        hdr.pack(fill=tk.X, padx=18)
        tk.Label(hdr, text="LEADERBOARD", font=F_TITLE, bg=SURF, fg=TXT).pack(side=tk.LEFT)

        sep(right, padx=12, pady=0)

        ff = tk.Frame(right, bg=SURF, pady=8)
        ff.pack(fill=tk.X, padx=14)
        ff.grid_columnconfigure(1, weight=1)
        ff.grid_columnconfigure(3, weight=1)

        self._fd = tk.StringVar(value="All")
        self._fm = tk.StringVar(value="All")
        self._fn = tk.StringVar()

        def lbl(t, r, c):
            tk.Label(ff, text=t, font=F_SMALL, bg=SURF, fg=TXT2).grid(
                row=r, column=c, sticky="w", padx=(0, 3))

        lbl("DIFF:", 0, 0)
        ttk.Combobox(ff, textvariable=self._fd, values=["All","Easy","Medium","Hard"],
                     state="readonly", width=8).grid(row=0, column=1, sticky="ew", padx=(0,8))
        lbl("MODE:", 0, 2)
        ttk.Combobox(ff, textvariable=self._fm, values=["All","Standard","Time Attack","Chaos"],
                     state="readonly", width=11).grid(row=0, column=3, sticky="ew")
        lbl("SEARCH:", 1, 0)
        tk.Entry(ff, textvariable=self._fn, bg=CARD2, fg=TXT, insertbackground=TXT,
                 relief=tk.FLAT, font=F_SMALL, width=28,
                 highlightthickness=1, highlightbackground=BDR).grid(
            row=1, column=1, columnspan=3, sticky="ew", pady=(5, 0))

        for var in (self._fd, self._fm):
            var.trace_add("write", lambda *_: self._refresh_lb())
        self._fn.trace_add("write", lambda *_: self._refresh_lb())

        tf = tk.Frame(right, bg=SURF)
        tf.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 10))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        cols = ("Rank","Name","Score","Time","Diff","Mode","Result")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                  selectmode="none", height=24)
        widths = [38, 110, 65, 55, 55, 90, 55]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.tag_configure("win",  foreground=SUCC)
        self.tree.tag_configure("loss", foreground=DANG)
        self.tree.tag_configure("tie",  foreground=WARN)

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def on_show(self):
        self.combo["values"] = self.app.dm.unique_names()
        self._refresh_players()
        self._refresh_lb()
        self._refresh_stats()

    def _refresh_players(self):
        for w in self._players_frame.winfo_children():
            w.destroy()
        names = self.app.dm.unique_names()
        if not names:
            tk.Label(self._players_frame, text="No players yet — be the first!",
                     font=F_SMALL, bg=CARD, fg=TXT2).pack(anchor="w", pady=6)
            return
        MEDAL = ["🥇", "🥈", "🥉"]
        def _hs(n):
            ps = self.app.dm.player_stats(n)
            return ps["high_score"] if ps else 0
        ranked = sorted(names, key=_hs, reverse=True)
        for idx, name in enumerate(ranked):
            ps   = self.app.dm.player_stats(name)
            icon = MEDAL[idx] if idx < 3 else "👤"
            if ps and ps["played"]:
                wr   = f"{ps['wins']/ps['played']*100:.0f}%"
                info = f"W{ps['wins']} L{ps['losses']} T{ps['ties']}   ★{ps['high_score']:,}   {wr}"
                res_col = SUCC if ps["wins"] >= ps["losses"] else DANG
            else:
                info = "New Player"; res_col = TXT2
            row = tk.Frame(self._players_frame, bg=CARD2, pady=6, padx=10, cursor="hand2")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{icon} {name}", font=("Georgia", 10, "bold"),
                     bg=CARD2, fg=TXT, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=info, font=F_SMALL, bg=CARD2, fg=res_col, anchor="e").pack(side=tk.RIGHT)
            def _make_sel(n=name):
                def _sel(e=None): self._select_player(n)
                return _sel
            cb = _make_sel(name)
            row.bind("<Button-1>", cb)
            for child in row.winfo_children():
                child.bind("<Button-1>", cb)
            def _enter(e, f=row):
                hv = _shade(CARD2, 1.25); f.config(bg=hv)
                for c in f.winfo_children():
                    try: c.config(bg=hv)
                    except Exception: pass
            def _leave(e, f=row):
                f.config(bg=CARD2)
                for c in f.winfo_children():
                    try: c.config(bg=CARD2)
                    except Exception: pass
            row.bind("<Enter>", _enter)
            row.bind("<Leave>", _leave)

    def _select_player(self, name: str):
        self.app.player.set(name)
        self._refresh_stats()
        self.combo.selection_clear()

    def _refresh_lb(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = self.app.dm.get_leaderboard(self._fd.get(), self._fm.get(), self._fn.get())
        for rank, e in enumerate(rows[:60], 1):
            res = e.get("result", "")
            self.tree.insert("", "end",
                values=(rank, e["name"], e.get("score", e.get("pieces", 0)),
                        e["time"], e.get("diff","?"), e.get("mode","?"), res.upper()),
                tags=(res,))

    def _refresh_stats(self):
        name = self.app.player.get().strip()
        ps   = self.app.dm.player_stats(name)
        if ps and ps["played"] > 0:
            wr = f"{ps['wins']/ps['played']*100:.0f}%"
            streak = ps.get("current_streak", 0)
            best_s = ps.get("best_streak", 0)
            streak_txt = (f"🔥 {streak} win streak!" if streak >= 2
                          else f"Best streak: {best_s}")
            self._slbl.config(
                text=(f"Played: {ps['played']}   W {ps['wins']} / "
                      f"L {ps['losses']} / T {ps['ties']}\n"
                      f"High Score: {ps['high_score']:,}   Win Rate: {wr}   {streak_txt}"))
        else:
            self._slbl.config(text="─  No history found for this player.")

    def _go_mode(self):
        name = self.app.player.get().strip() or "Anonymous"
        self.app.player.set(name)
        self.app.show("mode")


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 ─ GAME MODE
# ═══════════════════════════════════════════════════════════════════════════════
class ModeScreen(tk.Frame):
    MODES = [
        ("♟", "STANDARD",    "Standard",    "Classic Reversi.\nNo time limit.\nPlay at your pace.",          ACC,  "#ffffff"),
        ("⏱", "TIME ATTACK", "Time Attack", "3 minutes on the clock.\nScore as many as you can.\nEvery move counts.", WARN, BG),
        ("⚡", "Chaos",       "Chaos",       "30-sec per move limit.\nThink fast or lose.\nChaos mode.",     DANG, "#ffffff"),
    ]
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()
    def _build(self):
        tk.Label(self, text="SELECT MODE", font=F_TITLE, bg=BG, fg=TXT).pack(pady=(52, 4))
        tk.Label(self, text="How do you want to play today?", font=F_BODY, bg=BG, fg=TXT2).pack()
        sep(self, padx=100, pady=18)
        row = tk.Frame(self, bg=BG); row.pack()
        for icon, title, val, desc, color, fg in self.MODES:
            self._card(row, icon, title, val, desc, color, fg)
        sep(self, padx=100, pady=20)
        mkbtn(self, "◀  Back", lambda: self.app.show("start"), bg=CARD2, fg=TXT2, padx=22).pack()
    def _card(self, parent, icon, title, val, desc, color, fg):
        f = tk.Frame(parent, bg=CARD, width=255, height=295,
                     highlightthickness=1, highlightbackground=color)
        f.pack(side=tk.LEFT, padx=14); f.pack_propagate(False)
        tk.Label(f, text=icon, font=("Segoe UI Emoji", 32), bg=CARD, fg=color).pack(pady=(28, 4))
        tk.Label(f, text=title, font=F_HEAD, bg=CARD, fg=color).pack()
        sep(f, padx=20, pady=8)
        tk.Label(f, text=desc, font=F_BODY, bg=CARD, fg=TXT2, justify=tk.CENTER).pack(pady=4)
        def sel(v=val):
            self.app.game_mode.set(v); self.app.show("difficulty")
        mkbtn(f, "SELECT  →", sel, bg=color, fg=BG if fg==BG else TXT,
              padx=0, pady=9).pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
    def on_show(self): pass


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 ─ DIFFICULTY
# ═══════════════════════════════════════════════════════════════════════════════
class DifficultyScreen(tk.Frame):
    DIFFS = [
        ("😌","EASY",  "Easy",  SUCC,"Random AI moves.\nPerfect for beginners.\nJust have fun!","Random Strategy"),
        ("⚡","MEDIUM","Medium",WARN,"Neural network model.\nLearned from thousands\nof games.","Machine Learning"),
        ("💀","HARD",  "Hard",  DANG,"Neural Net + Minimax\nalpha-beta depth-4.\nGood luck.","ML + Minimax"),
    ]
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()
    def _build(self):
        tk.Label(self, text="SELECT DIFFICULTY", font=F_TITLE, bg=BG, fg=TXT).pack(pady=(52, 4))
        self._mode_lbl = tk.Label(self, text="", font=F_BODY, bg=BG, fg=NEON)
        self._mode_lbl.pack()
        sep(self, padx=100, pady=18)
        row = tk.Frame(self, bg=BG); row.pack()
        for icon, title, val, color, desc, strategy in self.DIFFS:
            self._card(row, icon, title, val, color, desc, strategy)
        sep(self, padx=100, pady=20)
        mkbtn(self, "◀  Back", lambda: self.app.show("mode"), bg=CARD2, fg=TXT2, padx=22).pack()
    def _card(self, parent, icon, title, val, color, desc, strategy):
        f = tk.Frame(parent, bg=CARD, width=255, height=330,
                     highlightthickness=1, highlightbackground=color)
        f.pack(side=tk.LEFT, padx=14); f.pack_propagate(False)
        tk.Label(f, text=icon, font=("Segoe UI Emoji", 30), bg=CARD, fg=color).pack(pady=(22, 4))
        tk.Label(f, text=title, font=F_HEAD, bg=CARD, fg=color).pack()
        tk.Label(f, text=f"  {strategy}  ", font=F_SMALL, bg=CARD2, fg=TXT2, padx=6, pady=3).pack(pady=(5,0))
        sep(f, padx=20, pady=8)
        tk.Label(f, text=desc, font=F_BODY, bg=CARD, fg=TXT2, justify=tk.CENTER).pack(pady=4)
        if val == "Medium":
            ok = self.app.ml_med.ok
        elif val == "Hard":
            ok = self.app.ml_hard.ok
        else:
            ok = None
        if ok is not None:
            tk.Label(f, text="✔ ML Loaded" if ok else "✘ No ML file",
                     font=F_SMALL, bg=CARD, fg=SUCC if ok else WARN).pack()
        def sel(v=val):
            self.app.difficulty.set(v); self.app.show("game")
        mkbtn(f, "PLAY  →", sel, bg=color, fg=BG,
              padx=0, pady=9).pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
    def on_show(self):
        self._mode_lbl.config(text=f"Mode: {self.app.game_mode.get()}")


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 ─ GAME BOARD   (Undo / Hint / Move-History-Log)
# ═══════════════════════════════════════════════════════════════════════════════
class GameScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        # ── Core game state ───────────────────────────────────────────────────
        self.board       = []
        self.cur_player  = BLACK
        self.game_over   = False
        self.animating   = False
        self.start_time  = 0
        self.timer_run   = False
        self.score       = 0
        self.delta       = 0
        self.turn_count  = 0
        self.last_move_t = 0
        self.move_log    = []
        self.confetti_p  = []
        self.X = []
        self.y = []
        # ── New v5 state ──────────────────────────────────────────────────────
        self.board_history: list = []   # stack of (board, score, delta, turn, log_copy)
        self.hint_count    = MAX_HINTS
        self._active_hint  = None       # (r,c) of best-hint cell
        self.piece_track: list = []     # [(turn, black_cnt, white_cnt), …]
        self.best_flip_combo = 0        # max player flips in one move this game
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # ── Top bar ───────────────────────────────────────────────────────────
        bar = tk.Frame(self, bg=SURF, height=52)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        self._lbl_info  = tk.Label(bar, text="", font=("Georgia", 11, "italic"),
                                    bg=SURF, fg=TXT)
        self._lbl_info.pack(side=tk.LEFT, padx=12)
        self._lbl_score = tk.Label(bar, text="Score: 0", font=("Georgia", 13, "bold"),
                                    bg=SURF, fg=ACC)
        self._lbl_score.pack(side=tk.LEFT, padx=6)

        # Right-side controls
        self._lbl_timer = tk.Label(bar, text="⏱  00:00", font=("Georgia", 13, "bold"),
                                    bg=SURF, fg=TXT2)
        self._lbl_timer.pack(side=tk.RIGHT, padx=12)
        mkbtn(bar, "🏳 Surrender", self._surrender,
              bg=CARD, fg=DANG, padx=8, pady=5, font=F_SMALL).pack(side=tk.RIGHT, padx=3)
        mkbtn(bar, "⏏ Menu", self._confirm_exit,
              bg=CARD, fg=TXT2, padx=8, pady=5, font=F_SMALL).pack(side=tk.RIGHT, padx=3)

        # ── Undo button ───────────────────────────────────────────────────────
        self._undo_btn = mkbtn(bar, "↩ Undo", self._undo,
                               bg=CARD2, fg=WARN, padx=8, pady=5, font=F_SMALL)
        self._undo_btn.pack(side=tk.RIGHT, padx=3)

        # ── Hint button ───────────────────────────────────────────────────────
        self._hint_btn = mkbtn(bar, f"💡 Hint ({MAX_HINTS})", self._hint,
                               bg=CARD2, fg=HINT_COL, padx=8, pady=5, font=F_SMALL)
        self._hint_btn.pack(side=tk.RIGHT, padx=3)

        # ── Placement guide toggle ─────────────────────────────────────────────
        self._guide_btn = mkbtn(bar, "👁 Guide: ON", self._toggle_guide,
                                bg=CARD2, fg=NEON, padx=8, pady=5, font=F_SMALL)
        self._guide_btn.pack(side=tk.RIGHT, padx=3)

        # ── Main area ─────────────────────────────────────────────────────────
        main = tk.Frame(self, bg=BG)
        main.pack(fill=tk.BOTH, expand=True)

        # Sidebar (right)
        self._sb = tk.Frame(main, bg=SURF, width=190)
        self._sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._sb.pack_propagate(False)
        self._build_sidebar()

        # Canvas + Move-Log column (left)
        left_col = tk.Frame(main, bg=BG)
        left_col.pack(fill=tk.BOTH, expand=True)

        # Canvas area (fills most of left_col)
        cw = tk.Frame(left_col, bg=BG)
        cw.pack(fill=tk.BOTH, expand=True)
        cs = CELL_SIZE * BOARD_SIZE
        self.canvas = tk.Canvas(cw, width=cs, height=cs, bg=BOARD_BG,
                                highlightthickness=3, highlightbackground=ACC2)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        self.canvas.bind("<Button-1>", self._click)
        self._board_bg_img = None   # will hold the PhotoImage reference

        # ── Move History Log strip at the bottom ──────────────────────────────
        log_f = tk.Frame(left_col, bg=CARD2, height=82)
        log_f.pack(fill=tk.X, padx=0)
        log_f.pack_propagate(False)

        tk.Label(log_f, text="MOVE LOG", font=("Georgia", 8, "bold italic"),
                 bg=CARD2, fg=ACC).pack(side=tk.LEFT, padx=(10, 6), pady=4)

        log_sb = ttk.Scrollbar(log_f, orient="vertical")
        log_sb.pack(side=tk.RIGHT, fill=tk.Y, pady=4, padx=(0, 6))

        self._log_box = tk.Text(
            log_f, height=4, font=("Georgia", 9),
            bg=CARD, fg=TXT2, relief=tk.FLAT, bd=0,
            state=tk.DISABLED, wrap=tk.NONE,
            yscrollcommand=log_sb.set,
            highlightthickness=0
        )
        self._log_box.pack(fill=tk.BOTH, expand=True, pady=(2, 4))
        log_sb.config(command=self._log_box.yview)

    def _build_sidebar(self):
        s = self._sb
        tk.Label(s, text="GAME", font=("Georgia", 9, "bold italic"),
                 bg=SURF, fg=ACC).pack(pady=(16, 4))
        self._lbl_b = tk.Label(s, text="⬛ You: 2", font=F_BODY, bg=SURF, fg=TXT)
        self._lbl_b.pack(pady=2)
        self._lbl_w = tk.Label(s, text="⬜ AI: 2",  font=F_BODY, bg=SURF, fg=TXT)
        self._lbl_w.pack(pady=2)
        sep(self._sb, padx=16, pady=8)
        tk.Label(s, text="TURN", font=("Georgia", 9, "bold italic"), bg=SURF, fg=ACC).pack()
        self._lbl_turn = tk.Label(s, text="YOUR TURN", font=("Georgia", 10, "bold"),
                                   bg=SURF, fg=SUCC)
        self._lbl_turn.pack(pady=(2, 8))
        tk.Label(s, text="DELTA", font=("Georgia", 9, "bold italic"), bg=SURF, fg=ACC).pack()
        self._lbl_delta = tk.Label(s, text="+0", font=F_HEAD, bg=SURF, fg=SUCC)
        self._lbl_delta.pack(pady=(2, 0))
        sep(self._sb, padx=16, pady=8)
        tk.Label(s, text="DIFFICULTY", font=("Georgia", 9, "bold italic"), bg=SURF, fg=ACC).pack()
        self._lbl_diff = tk.Label(s, text="—", font=F_HEAD, bg=SURF, fg=WARN)
        self._lbl_diff.pack()
        tk.Label(s, text="MODE", font=("Georgia", 9, "bold italic"),
                 bg=SURF, fg=ACC).pack(pady=(10, 2))
        self._lbl_mode = tk.Label(s, text="—", font=F_SMALL, bg=SURF, fg=TXT2)
        self._lbl_mode.pack()
        sep(self._sb, padx=16, pady=8)
        tk.Label(s, text="CORNERS", font=("Georgia", 9, "bold italic"), bg=SURF, fg=ACC).pack()
        self._lbl_corners = tk.Label(s, text="You: 0 / AI: 0", font=F_SMALL, bg=SURF, fg=NEON)
        self._lbl_corners.pack(pady=(2, 0))

        # ── AI Speech Bubble ──────────────────────────────────────────────────
        sep(self._sb, padx=16, pady=8)
        bubble_wrap = tk.Frame(s, bg=SURF)
        bubble_wrap.pack(fill=tk.X, padx=8)
        tk.Label(bubble_wrap, text="♟ Opponent:", font=("Georgia", 8, "bold italic"),
                 bg=SURF, fg=TXT2).pack(anchor="w")
        self._bubble_frame = tk.Frame(bubble_wrap, bg=CARD2,
                                       highlightthickness=1,
                                       highlightbackground=BDR)
        self._bubble_frame.pack(fill=tk.X, pady=(3, 0))
        self._taunt_lbl = tk.Label(
            self._bubble_frame,
            text="Let's see what\nyou've got.",
            font=("Georgia", 9, "italic"),
            bg=CARD2, fg=TXT,
            wraplength=155, justify=tk.LEFT,
            padx=8, pady=7)
        self._taunt_lbl.pack(fill=tk.X)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    def on_show(self):
        self._lbl_diff.config(text=self.app.difficulty.get())
        self._lbl_mode.config(text=self.app.game_mode.get())
        # Sync guide button to current app setting
        self._sync_guide_btn()
        self._start()

    def _toggle_guide(self):
        self.app.show_hints = not self.app.show_hints
        self._sync_guide_btn()
        self._draw()

    def _sync_guide_btn(self):
        if self.app.show_hints:
            self._guide_btn.config(text="👁 Guide: ON",  fg=NEON)
        else:
            self._guide_btn.config(text="👁 Guide: OFF", fg=TXT2)

    def _start(self):
        # Chaos mode board modifiers
        global BOARD_SIZE
        if (self.app.game_mode.get() == "Chaos"):
            BOARD_SIZE = 12
        else : BOARD_SIZE = 8
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        mid = BOARD_SIZE//2
        self.board[mid - 1][mid - 1]  = self.board[mid][mid] = WHITE
        self.board[mid - 1][mid]  = self.board[mid][mid - 1] = BLACK
        cs = CELL_SIZE * BOARD_SIZE
        
        if (self.app.game_mode.get() == "Chaos"):
            self.chaos_manager = ChaosManager(self)
            self.chaos_animator = ChaosAnimator(self)
        else : 
            self.chaos_manager = None
            self.chaos_animator = None
        
        # Normal stuff
        self.canvas.config(width = cs, height = cs)
        self.cur_player   = BLACK
        self.game_over    = False
        self.animating    = False
        self.score = self.delta = self.turn_count = 0
        self.start_time   = self.last_move_t = time.time()
        self.timer_run    = True
        self.move_log     = []
        self.confetti_p   = []
        # v5 resets
        self.board_history   = []
        self.hint_count      = MAX_HINTS
        self._active_hint    = None
        self.piece_track     = []
        self.best_flip_combo = 0
        self._taunt_job      = None
        # Reset hint button label
        self._hint_btn.config(text=f"💡 Hint ({MAX_HINTS})")
        self._undo_btn.config(state=tk.NORMAL)
        # Clear move log widget
        self._log_box.config(state=tk.NORMAL)
        self._log_box.delete("1.0", tk.END)
        self._log_box.config(state=tk.DISABLED)
        # ── Load board background image ────────────────────────────────────────
        self._load_board_bg()
        # Record initial piece state
        self._snapshot_pieces()
        self._say(_pick_taunt("game_start"))
        self._draw()
        self._tick()

    @staticmethod
    def _cell_cx(c : int) -> int:
        cw = CELL_SIZE
        return int(c * cw + cw * 0.5)
    
    @staticmethod
    def _cell_cy(c : int) -> int:
        cw = CELL_SIZE
        return int(r * ch + ch * 0.5)
        
    def _load_board_bg(self):
        """Load tan_board_v2.png, scale to canvas size, keep reference."""
        cs = CELL_SIZE * BOARD_SIZE
        d  = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(d, "tan_board_v2.png")
        if PIL_OK and os.path.exists(img_path):
            try:
                raw = Image.open(img_path).resize((cs, cs), Image.Resampling.LANCZOS)
                self._board_bg_img = ImageTk.PhotoImage(raw)
                return
            except Exception:
                pass
        self._board_bg_img = None

    # ── Speech bubble helper ──────────────────────────────────────────────────
    def _say(self, text: str, duration_ms: int = 4500):
        """Display a taunt in the AI speech bubble for duration_ms."""
        if not text:
            return
        if self._taunt_job:
            try:
                self.after_cancel(self._taunt_job)
            except Exception:
                pass
            self._taunt_job = None
        try:
            self._taunt_lbl.config(text=text)
            self._bubble_frame.config(highlightbackground=NEON)
            self._taunt_job = self.after(
                duration_ms,
                lambda: self._bubble_frame.config(highlightbackground=ACC2)
                        if self._taunt_lbl.winfo_exists() else None)
        except Exception:
            pass

    # ── Piece snapshot for piece_track ────────────────────────────────────────
    def _snapshot_pieces(self):
        bc = sum(row.count(BLACK) for row in self.board)
        wc = sum(row.count(WHITE) for row in self.board)
        self.piece_track.append((self.turn_count, bc, wc))

    # ── Timer ─────────────────────────────────────────────────────────────────
    def _tick(self):
        if not self.timer_run or self.game_over:
            return
        now  = time.time()
        mode = self.app.game_mode.get()
        if "Time Attack" in mode:
            left = max(0, 180 - int(now - self.start_time))
            m, s = divmod(left, 60)
            self._lbl_timer.config(text=f"⏱  {m:02d}:{s:02d}",
                                    fg=DANG if left <= 30 else TXT2)
            if left == 0:
                self._end(timeout=True); return
        else:
            elapsed = int(now - self.start_time)
            m, s = divmod(elapsed, 60)
            self._lbl_timer.config(text=f"⏱  {m:02d}:{s:02d}", fg=TXT2)
        self.after(1000, self._tick)

    # ── Drawing ───────────────────────────────────────────────────────────────
    # ── Cell-centre helpers aligned to board image grid ──────────────────────
    @staticmethod
    def _cell_cx(c: int) -> int:
        return int(BOARD_IMG_OX + (c + 0.5) * BOARD_IMG_CW)

    @staticmethod
    def _cell_cy(r: int) -> int:
        return int(BOARD_IMG_OY + (r + 0.5) * BOARD_IMG_CH)

    def _draw(self, exclude=None):
        if exclude is None:
            exclude = []
        self.canvas.delete("el")

        # ── Board image first — it already contains grid lines and star dots ──
        if self._board_bg_img:
            self.canvas.create_image(0, 0, image=self._board_bg_img,
                                     anchor="nw", tags="el")
        else:
            # Fallback if image not found: plain mahogany tiles
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    x0 = int(BOARD_IMG_OX + c * BOARD_IMG_CW)
                    y0 = int(BOARD_IMG_OY + r * BOARD_IMG_CH)
                    x1 = int(BOARD_IMG_OX + (c+1) * BOARD_IMG_CW)
                    y1 = int(BOARD_IMG_OY + (r+1) * BOARD_IMG_CH)
                    tile = "#8B5A2B" if (r+c) % 2 == 0 else "#7A4E25"
                    self.canvas.create_rectangle(x0, y0, x1, y1,
                        fill=tile, outline=BOARD_LN, width=1, tags="el")

        # ── Hint cells (placement guide) ──────────────────────────────────────
        if self.app.show_hints and self.cur_player == BLACK:
            hints = valid_moves(self.board, self.cur_player)
        else:
            hints = []

        # Piece radius fitted to image cell size
        p = int(min(BOARD_IMG_CW, BOARD_IMG_CH) / 2) - 5

        bc = wc = 0
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                cx = self._cell_cx(c)
                cy = self._cell_cy(r)
                v  = self.board[r][c]

                if v == BLACK:
                    bc += 1
                    if (r, c) not in exclude:
                        # Drop shadow
                        self.canvas.create_oval(cx-p+3, cy-p+4, cx+p+3, cy+p+4,
                            fill="#1A0800", outline="", stipple="gray50", tags="el")
                        # Ebony disc
                        self.canvas.create_oval(cx-p, cy-p, cx+p, cy+p,
                            fill=PIECE_BLACK_FILL,
                            outline=PIECE_BLACK_OUTLINE, width=3, tags="el")
                        # Gloss highlight top-left
                        self.canvas.create_oval(cx-p+5, cy-p+5,
                                                cx-p+5+int(p*0.7), cy-p+5+int(p*0.45),
                            fill="#4A3020", outline="", tags="el")

                elif v == WHITE:
                    wc += 1
                    if (r, c) not in exclude:
                        # Drop shadow
                        self.canvas.create_oval(cx-p+3, cy-p+4, cx+p+3, cy+p+4,
                            fill="#1A0800", outline="", stipple="gray50", tags="el")
                        # Ivory disc
                        self.canvas.create_oval(cx-p, cy-p, cx+p, cy+p,
                            fill=PIECE_WHITE_FILL,
                            outline=PIECE_WHITE_OUTLINE, width=2, tags="el")
                        # Warm inner sheen
                        self.canvas.create_oval(cx-p+3, cy-p+3, cx+p-3, cy+p-3,
                            fill="#F0E6CC", outline="", tags="el")
                        # Gloss spot
                        self.canvas.create_oval(cx-p+7, cy-p+6,
                                                cx-p+7+int(p*0.55), cy-p+6+int(p*0.35),
                            fill="#FFFDF5", outline="", tags="el")

                elif (r, c) in hints:
                    if self._active_hint and (r, c) == self._active_hint:
                        # Gold ring + star = best hint cell
                        self.canvas.create_oval(cx-p+2, cy-p+2, cx+p-2, cy+p-2,
                            fill="", outline=HINT_COL, width=2, tags="el")
                        self.canvas.create_oval(cx-9, cy-9, cx+9, cy+9,
                            fill=HINT_COL, outline="", tags="el")
                        self.canvas.create_text(cx, cy, text="★", fill=BG,
                            font=("Georgia", 9, "bold"), tags="el")
                    else:
                        # Subtle gold dot
                        self.canvas.create_oval(cx-6, cy-6, cx+6, cy+6,
                            fill=HINT_COL, outline="", stipple="gray50", tags="el")
                        self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3,
                            fill=HINT_COL, outline="", tags="el")

        # Corner live tracker
        bc_corner = sum(1 for r, c in CORNERS if self.board[r][c] == BLACK)
        wc_corner = sum(1 for r, c in CORNERS if self.board[r][c] == WHITE)
        self._lbl_corners.config(text=f"You: {bc_corner} / AI: {wc_corner}")

        name = self.app.player.get()
        self._lbl_b.config(text=f"🕳 {name}: {bc}")
        self._lbl_w.config(text=f"🌙 AI: {wc}")
        self._lbl_score.config(text=f"Score: {self.score:,}")
        turn_name = name if self.cur_player == BLACK else "AI"
        turn_col  = SUCC if self.cur_player == BLACK else WARN
        self._lbl_turn.config(text=f"{turn_name}'s Turn", fg=turn_col)
        dc_col = SUCC if self.delta >= 0 else DANG
        self._lbl_delta.config(
            text=(f"+{self.delta}" if self.delta >= 0 else str(self.delta)), fg=dc_col)
        self._lbl_info.config(text=f"Turn {self.turn_count}")

    # ── Input ─────────────────────────────────────────────────────────────────
    def _click(self, e):
        if self.game_over or self.cur_player != BLACK or self.animating:
            return
        # Map pixel → board cell using the image-offset grid
        c  = int(e.x / CELL_SIZE)
        r  = int(e.y / CELL_SIZE)
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
            return
        if (r, c) in valid_moves(self.board, BLACK):
            self._push_history()
            self.animating    = True
            self._active_hint = None
            flipped = self._do_move(self.board, BLACK, r, c)

            # AI reacts to player move
            n_flip    = len(flipped)
            is_corner = (r, c) in CORNERS
            move_dt   = time.time() - self.last_move_t

            if is_corner:
                self._say(_pick_taunt("player_corner"))
            elif n_flip >= 5:
                self._say(_pick_taunt("player_big_flip", n=n_flip))
            elif move_dt > 12:
                self._say(_pick_taunt("player_slow"))

            self._anim(flipped, PIECE_BLACK_FILL, PIECE_WHITE_FILL, self._switch)

    # ── Board-history stack ───────────────────────────────────────────────────
    def _push_history(self):
        """Push current board state onto the undo stack."""
        self.board_history.append({
            "board":      copy.deepcopy(self.board),
            "score":      self.score,
            "delta":      self.delta,
            "turn_count": self.turn_count,
            "move_log":   list(self.move_log),
            "piece_track":list(self.piece_track),
            "best_flip":  self.best_flip_combo,
        })

    def _undo(self):
        """Undo the last player+AI pair of moves."""
        if self.game_over or self.animating:
            return
        # We need at least 1 saved state (state before player's last move)
        if not self.board_history:
            return
        state = self.board_history.pop()
        self.board           = state["board"]
        self.score           = state["score"]
        self.delta           = state["delta"]
        self.turn_count      = state["turn_count"]
        self.move_log        = state["move_log"]
        self.piece_track     = state["piece_track"]
        self.best_flip_combo = state["best_flip"]
        self.cur_player      = BLACK
        self._active_hint    = None
        # Rebuild move log widget
        self._rebuild_log_widget()
        self._draw()
        if not self.board_history:
            self._undo_btn.config(state=tk.DISABLED)

    def _rebuild_log_widget(self):
        self._log_box.config(state=tk.NORMAL)
        self._log_box.delete("1.0", tk.END)
        cols = "ABCDEFGHIJKL"
        for i, entry in enumerate(self.move_log, 1):
            pos = entry.get("pos", (0, 0))
            cell = f"{cols[pos[1]]}{pos[0]+1}"
            player_label = entry["player"]
            side = "⬛" if player_label != "AI" else "⬜"
            line = f"{i:>3}. {side} {player_label:<12} → {cell}   (+{entry['flipped']} flip)\n"
            self._log_box.insert(tk.END, line)
        self._log_box.config(state=tk.DISABLED)
        self._log_box.see(tk.END)

    # ── Hint ──────────────────────────────────────────────────────────────────
    def _hint(self):
        if self.game_over or self.animating or self.cur_player != BLACK:
            return
        if self.hint_count <= 0:
            messagebox.showinfo("No Hints Left", "You've used all your hints for this game!")
            return
        best = best_move_for_black(self.app, self.board)
        if not best:
            return
        self.hint_count  -= 1
        self._active_hint = best
        self._hint_btn.config(text=f"💡 Hint ({self.hint_count})")
        if self.hint_count == 0:
            self._hint_btn.config(state=tk.DISABLED)
        self._draw()

    # ── Move logic ────────────────────────────────────────────────────────────
    def _do_move(self, board, player, r, c):
        now     = time.time()
        flipped = apply_move(board, player, r, c)
        n       = len(flipped)
        dt      = now - self.last_move_t
        self.last_move_t = now
        old     = self.score
        if player == BLACK:
            self.score += int((n**2.1 * 5) + max(0, 130 - (dt*5)**3.5))
            # Track highest flip combo
            if n > self.best_flip_combo:
                self.best_flip_combo = n
        else:
            self.score -= int(n**1.7 * 13)
        self.delta = self.score - old

        player_label = self.app.player.get() if player == BLACK else "AI"
        entry = {
            "turn":    self.turn_count,
            "player":  player_label,
            "pos":     (r, c),
            "flipped": n,
            "time":    round(dt, 2),
            "score":   self.score,
            "delta":   self.delta,
            "board_state": copy.deepcopy(self.board)
        }
        self.move_log.append(entry)
        self.turn_count += 1
        if (self.app.game_mode.get() == "Chaos") : 
            self.chaos_manager.turn_count = self.turn_count
            side, events = self.chaos_manager.next_event()
            if side and events:
                self.chaos_manager.event_selector(side, events)
            events = self.chaos_manager.next_event()

        cols = "ABCDEFGHIJKL"
        cell = f"{cols[c]}{r+1}"
        side = "⬛" if player == BLACK else "⬜"
        line = (f"{len(self.move_log):>3}. {side} {player_label:<12} → {cell}"
                f"   (+{n} flip)\n")
        self._log_box.config(state=tk.NORMAL)
        self._log_box.insert(tk.END, line)
        self._log_box.config(state=tk.DISABLED)
        self._log_box.see(tk.END)
        
        # Snapshot piece counts for line chart
        self._snapshot_pieces()
        for entry in self.move_log:
            r, c = entry["pos"]
            board_snapshot = entry.get("board_state")  # you may need to store this
            self.X.append(self.encode_board(board_snapshot))
            self.y.append(self.encode_move(r, c))
        return flipped
    
    def encode_board(self, board):
        arr = np.zeros((BOARD_SIZE,BOARD_SIZE,1), dtype=np.float32)
        for r in range(8):
            for c in range(8):
                if board[r][c] == BLACK:
                    arr[r,c,0] = 1
                elif board[r][c] == WHITE:
                    arr[r,c,0] = -1
        return arr

    def encode_move(self, r, c):
        y = np.zeros(144, dtype=np.float32)
        y[r*BOARD_SIZE + c] = 1.0
        return y
    # ── Animation ─────────────────────────────────────────────────────────────
    def _anim(self, flipped, new_c, old_c, cb, step=0):
        frames = 6
        if step <= frames * 2:
            ratio = 1.0 - step/frames if step <= frames else (step-frames)/frames
            color = old_c if step <= frames else new_c
            self._draw(exclude=flipped)
            p = int(min(BOARD_IMG_CW, BOARD_IMG_CH) / 2) - 5
            for r, c in flipped:
                cx = self._cell_cx(c)
                cy = self._cell_cy(r)
                rx = max(1, int(p * ratio))
                ry = p
                self.canvas.create_oval(cx-rx, cy-ry, cx+rx, cy+ry,
                    fill=color, outline=BDR, width=2, tags="el")
            self.after(18, self._anim, flipped, new_c, old_c, cb, step+1)
        else:
            self.animating = False
            self._draw()
            cb()

    # ── Turn switching ─────────────────────────────────────────────────────────
    def _switch(self):
        self.cur_player = WHITE if self.cur_player == BLACK else BLACK
        if not valid_moves(self.board, self.cur_player):
            self.cur_player = WHITE if self.cur_player == BLACK else BLACK
            if not valid_moves(self.board, self.cur_player):
                self._end(); return
            if (self.app.game_mode.get() == "Chaos") and (self.turn_count >= 100):
                self._end(); return
        self._draw()
        # Allow undo button now that there's at least one saved state
        if self.board_history:
            self._undo_btn.config(state=tk.NORMAL)
        if self.cur_player == WHITE and not self.game_over:
            self.after(280, self._ai_turn)

    # ── AI ────────────────────────────────────────────────────────────────────
    def _ai_turn(self):
        moves = valid_moves(self.board, WHITE)
        if not moves:
            self._switch(); return
        diff = self.app.difficulty.get()
        if diff == "Easy":
            best = random.choice(moves)
        elif diff == "Medium":
            m = self.app.ml_med
            if m.ok:
                best_val = float("-inf"); best = moves[0]
                for r, c in moves:
                    tb = copy.deepcopy(self.board)
                    apply_move(tb, WHITE, r, c)
                    vw = valid_moves(tb, WHITE); vb = valid_moves(tb, BLACK)
                    v  = m.evaluate(tb, vw, vb) or 0
                    if v > best_val:
                        best_val, best = v, (r, c)
            else:
                best, mx = moves[0], -1
                for r, c in moves:
                    tb = copy.deepcopy(self.board)
                    apply_move(tb, WHITE, r, c)
                    wc = sum(row.count(WHITE) for row in tb)
                    if wc > mx:
                        mx, best = wc, (r, c)
        else:
            model = self.app.ml_hard if self.app.ml_hard.ok else None
            _, best = minimax(self.board, 4, float("-inf"), float("inf"), True, model)
            if not best:
                best = random.choice(moves)
        self.animating = True
        flipped = self._do_move(self.board, WHITE, best[0], best[1])

        # ── AI commentary ─────────────────────────────────────────────────────
        n_flip = len(flipped)
        is_corner = best in CORNERS
        bc = sum(row.count(BLACK) for row in self.board)
        wc = sum(row.count(WHITE) for row in self.board)
        remaining = sum(row.count(EMPTY) for row in self.board)

        if is_corner:
            self._say(_pick_taunt("corner_grab"))
        elif n_flip >= 5:
            self._say(_pick_taunt("big_flip", n=n_flip))
        elif remaining <= 12:
            self._say(_pick_taunt("few_moves_left"))
        elif wc > bc + 8:
            self._say(_pick_taunt("ai_winning"))
        elif bc > wc + 8:
            self._say(_pick_taunt("ai_losing"))
        elif random.random() < 0.15:   # occasional random comment
            key = random.choice(["ai_winning", "few_moves_left"])
            self._say(_pick_taunt(key))

        self._anim(flipped, PIECE_WHITE_FILL, PIECE_BLACK_FILL, self._switch)

    # ── Game end ──────────────────────────────────────────────────────────────
    def _end(self, timeout=False, surrendered=False):
        self.game_over = True
        self.timer_run = False
        self._draw()
        bc = sum(row.count(BLACK) for row in self.board)
        wc = sum(row.count(WHITE) for row in self.board)
        rt = int(time.time() - self.start_time)
        m, s = divmod(rt, 60)
        time_str    = f"{m:02d}:{s:02d}"
        final_score = self.score + bc*100 - wc*120
        diff = str(self.app.difficulty.get())
        mode = str(self.app.game_mode.get())
        np.savez(diff + " reversi_dataset.npz", X=np.array(self.X), y=np.array(self.y))
        print(f"Saved {len(np.array(self.X))} samples to {diff} reversi_dataset.npz")
        if surrendered or timeout:
            wc = 64; result = "loss"
            msg = "Time's Up! AI Wins." if timeout else "You Surrendered!"
        elif bc > wc: result, msg = "win",  "You WIN! 🎉"
        elif wc > bc: result, msg = "loss", "AI Wins! 😢"
        else:         result, msg = "tie",  "It's a DRAW! 🤝"

        corners = sum(1 for r, c in CORNERS if self.board[r][c] == BLACK)

        self.app.dm.add_entry(
            self.app.player.get(), bc, time_str,
            self.app.difficulty.get(), self.app.game_mode.get(), result, final_score,
            corners=corners, best_flip=self.best_flip_combo
        )

        # ── Evaluate achievements AFTER add_entry (stats are updated) ─────────
        new_ach = self.app.dm.evaluate_achievements(
            self.app.player.get(), result,
            self.app.difficulty.get(), rt, bc, wc,
            corners, self.best_flip_combo, list(self.piece_track)
        )

        self.app.play_sfx(result)
        if result == "win":
            self._spawn_confetti()
        delay = 1800 if result == "win" else 600
        self.after(delay, lambda: self.app.show(
            "postgame", result=result, msg=msg, bc=bc, wc=wc,
            final_score=final_score, time_str=time_str,
            move_log=list(self.move_log),
            piece_track=list(self.piece_track),
            corner_ctrl=corners,
            best_flip=self.best_flip_combo,
            new_achievements=new_ach))

    def _confirm_exit(self):
        if messagebox.askyesno("Exit", "Return to main menu? Progress will be lost."):
            self.timer_run = False
            self.app.show("start")

    def _surrender(self):
        if messagebox.askyesno("Surrender", "Are you sure you want to give up?"):
            self._end(surrendered=True)

    def _spawn_confetti(self):
        colors = ["#D4AF37","#F5F0DC","#8B5A2B","#C8A45A","#6BAF6B","#B84040","#F0C860"]
        for _ in range(110):
            x = random.randint(0, CELL_SIZE*BOARD_SIZE)
            y = random.randint(-400, -40)
            sz = random.randint(6, 12)
            pid = self.canvas.create_oval(x, y, x+sz, y+sz,
                fill=random.choice(colors), outline="", tags="confetti")
            self.confetti_p.append({"id": pid, "dx": random.uniform(-2,2),
                                     "dy": random.uniform(3,7)})
        self._tick_confetti()

    def _tick_confetti(self):
        if not self.game_over:
            return
        alive = False
        for p in self.confetti_p:
            self.canvas.move(p["id"], p["dx"], p["dy"])
            p["dy"] += 0.1
            coords = self.canvas.coords(p["id"])
            if coords and coords[1] < CELL_SIZE*BOARD_SIZE + 50:
                alive = True
        if alive:
            self.after(28, self._tick_confetti)
    
    # ── Chaos Mode ────────────────────────────────────────────────────────────
    def trigger_event_popup(self):
        # Ask ChaosManager to decide side + events
        side, events = self.chaos_manager.trigger_event()

        # Create popup window
        popup = tk.Toplevel(self)
        popup.title("Chaos Event Triggered!")

        # Header
        tk.Label(popup, text=f"{side} Chaos Event!", font=("Arial", 14, "bold")).pack(pady=10)

        # If player side → let them choose
        if side == "Player":
            tk.Label(popup, text="Pick one chaos power to unleash:").pack(pady=5)
            for event in events:
                btn = tk.Button(
                    popup,
                    text=event.name,
                    command=lambda e=event: self.apply_and_close(popup, e, side)
                )
                btn.pack(padx=10, pady=5)
        else:
            # AI side → auto apply
            tk.Label(popup, text=f"AI unleashes {events[0].name}!").pack(pady=10)
            self.apply_and_close(popup, events[0], side)

    def apply_and_close(self, popup, event, side):
        # Apply chaos effect
        self.chaos_manager.apply_event(event, side)
        # Close popup
        popup.destroy()
        # Refresh board
        self.draw_board()


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN 5 ─ FULL LEADERBOARD  (dedicated screen with player profile panel)
# ═══════════════════════════════════════════════════════════════════════════════
class LeaderboardFullScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=SURF, pady=0)
        bar.pack(fill=tk.X); bar.pack_propagate(False); bar.config(height=54)
        tk.Label(bar, text="📊  LEADERBOARD", font=F_TITLE,
                 bg=SURF, fg=TXT).pack(side=tk.LEFT, padx=20, pady=10)
        mkbtn(bar, "◀  Back to Menu", lambda: self.app.show("start"),
              bg=CARD2, fg=TXT2, padx=14, pady=8,
              font=F_BTN).pack(side=tk.RIGHT, padx=16, pady=8)
        sep(self, pady=0)

        content = tk.Frame(self, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        lb_f = tk.Frame(content, bg=SURF)
        lb_f.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        lb_f.grid_rowconfigure(1, weight=1); lb_f.grid_columnconfigure(0, weight=1)

        ff = tk.Frame(lb_f, bg=SURF, pady=8)
        ff.grid(row=0, column=0, sticky="ew", padx=12)
        self._fd2 = tk.StringVar(value="All")
        self._fm2 = tk.StringVar(value="All")
        self._fn2 = tk.StringVar()

        row1 = tk.Frame(ff, bg=SURF); row1.pack(fill=tk.X)
        tk.Label(row1, text="DIFF:", font=F_SMALL, bg=SURF, fg=TXT2).pack(side=tk.LEFT, padx=(0,4))
        ttk.Combobox(row1, textvariable=self._fd2,
                     values=["All","Easy","Medium","Hard"],
                     state="readonly", width=8).pack(side=tk.LEFT, padx=(0,12))
        tk.Label(row1, text="MODE:", font=F_SMALL, bg=SURF, fg=TXT2).pack(side=tk.LEFT, padx=(0,4))
        ttk.Combobox(row1, textvariable=self._fm2,
                     values=["All","Standard","Time Attack","Chaos"],
                     state="readonly", width=11).pack(side=tk.LEFT)

        row2 = tk.Frame(ff, bg=SURF); row2.pack(fill=tk.X, pady=(5,0))
        tk.Label(row2, text="SEARCH:", font=F_SMALL, bg=SURF, fg=TXT2).pack(side=tk.LEFT, padx=(0,4))
        tk.Entry(row2, textvariable=self._fn2, bg=CARD2, fg=TXT,
                 insertbackground=TXT, relief=tk.FLAT, font=F_SMALL, width=30,
                 highlightthickness=1, highlightbackground=BDR).pack(side=tk.LEFT)

        for var in (self._fd2, self._fm2):
            var.trace_add("write", lambda *_: self._refresh_lb2())
        self._fn2.trace_add("write", lambda *_: self._refresh_lb2())

        tf = tk.Frame(lb_f, bg=SURF)
        tf.grid(row=1, column=0, sticky="nsew", padx=10, pady=(6,10))
        tf.grid_rowconfigure(0, weight=1); tf.grid_columnconfigure(0, weight=1)

        cols = ("Rank","Name","Score","Time","Diff","Mode","Result")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings",
                                   selectmode="browse", height=24)
        widths = [40,130,72,58,60,100,58]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor="center")
        self._tree.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.tag_configure("win", foreground=SUCC)
        self._tree.tag_configure("loss", foreground=DANG)
        self._tree.tag_configure("tie",  foreground=WARN)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Right: profile panel
        self._prof_f = tk.Frame(content, bg=CARD)
        self._prof_f.grid(row=0, column=1, sticky="nsew")
        tk.Label(self._prof_f, text="PLAYER PROFILE",
                 font=F_HEAD, bg=CARD, fg=NEON).pack(pady=(18,0))
        sep(self._prof_f, padx=16, pady=6)
        self._prof_inner = tk.Frame(self._prof_f, bg=CARD)
        self._prof_inner.pack(fill=tk.BOTH, expand=True)
        tk.Label(self._prof_inner,
                 text="Click any row in the table\nto view a player's profile.",
                 font=F_BODY, bg=CARD, fg=TXT2, justify=tk.CENTER).pack(expand=True)

    def on_show(self):
        self._refresh_lb2()

    def _refresh_lb2(self):
        for i in self._tree.get_children():
            self._tree.delete(i)
        rows = self.app.dm.get_leaderboard(
            self._fd2.get(), self._fm2.get(), self._fn2.get())
        for rank, e in enumerate(rows[:100], 1):
            res = e.get("result","")
            self._tree.insert("", "end",
                values=(rank, e["name"],
                        e.get("score", e.get("pieces", 0)),
                        e["time"], e.get("diff","?"), e.get("mode","?"),
                        res.upper()),
                tags=(res,))

    def _on_select(self, _event):
        sel = self._tree.selection()
        if not sel: return
        name = self._tree.item(sel[0])["values"][1]
        self._show_profile(str(name))

    def _show_profile(self, name: str):
        for w in self._prof_inner.winfo_children():
            w.destroy()
        ps = self.app.dm.player_stats(name)

        tk.Label(self._prof_inner, text="👤", font=("Segoe UI Emoji", 28), bg=CARD).pack(pady=(16,2))
        tk.Label(self._prof_inner, text=name, font=F_TITLE, bg=CARD, fg=TXT).pack()
        sep(self._prof_inner, padx=24, pady=8)

        if not ps or not ps["played"]:
            tk.Label(self._prof_inner, text="No stats recorded.",
                     font=F_BODY, bg=CARD, fg=TXT2).pack(pady=16)
            return

        wr = ps["wins"] / ps["played"] * 100

        # ── Core stats ────────────────────────────────────────────────────────
        def _stat_row(label, val, col):
            r = tk.Frame(self._prof_inner, bg=CARD2, pady=7, padx=14)
            r.pack(fill=tk.X, padx=16, pady=2)
            tk.Label(r, text=label, font=F_SMALL, bg=CARD2, fg=TXT2, anchor="w").pack(side=tk.LEFT)
            tk.Label(r, text=val, font=("Georgia",10,"bold"), bg=CARD2, fg=col, anchor="e").pack(side=tk.RIGHT)

        _stat_row("Games Played", str(ps["played"]),          TXT)
        _stat_row("Wins",         str(ps["wins"]),             SUCC)
        _stat_row("Losses",       str(ps["losses"]),           DANG)
        _stat_row("Ties",         str(ps["ties"]),             WARN)
        _stat_row("Win Rate",     f"{wr:.1f}%",                NEON)
        _stat_row("Best Score",   f"{ps['high_score']:,}",     ACC)

        # ── NEW v5 stats ──────────────────────────────────────────────────────
        sep(self._prof_inner, padx=16, pady=5)
        tk.Label(self._prof_inner, text="ADVANCED STATS",
                 font=("Georgia",9,"bold"), bg=CARD, fg=TXT2).pack(pady=(2,4))

        # Win rate per difficulty
        ds = ps.get("diff_stats", {})
        for diff, col in [("Easy", SUCC), ("Medium", WARN), ("Hard", DANG)]:
            d = ds.get(diff, {"played": 0, "wins": 0})
            if d["played"]:
                dwr = f"{d['wins']/d['played']*100:.0f}%  ({d['wins']}/{d['played']})"
            else:
                dwr = "—"
            _stat_row(f"WR {diff}", dwr, col)

        # Avg corner control
        cg = ps.get("corner_games", 0)
        tc = ps.get("total_corners", 0)
        avg_corner = f"{tc/cg:.2f} / 4.0" if cg > 0 else "—"
        _stat_row("Avg Corners", avg_corner, NEON)

        # Highest flip combo
        hf = ps.get("highest_flip", 0)
        _stat_row("Best Flip Combo", f"{hf} pieces", ACC)

        # ── Win-rate bar ──────────────────────────────────────────────────────
        sep(self._prof_inner, padx=16, pady=6)
        bar_wrap = tk.Frame(self._prof_inner, bg=CARD, padx=16)
        bar_wrap.pack(fill=tk.X)
        tk.Label(bar_wrap, text="WIN RATE", font=("Georgia",8,"bold"),
                 bg=CARD, fg=TXT2).pack(anchor="w")
        bar_bg = tk.Frame(bar_wrap, bg=CARD2, height=10)
        bar_bg.pack(fill=tk.X, pady=(4,6))
        _wr = wr
        def _draw_bar(e=None, _bg=bar_bg, _p=_wr):
            w = _bg.winfo_width()
            if w > 1:
                for c in _bg.winfo_children(): c.destroy()
                fill_w = max(1, int(w * _p / 100))
                fill_col = SUCC if _p >= 50 else DANG
                tk.Frame(_bg, bg=fill_col, height=10, width=fill_w).place(x=0, y=0)
        bar_bg.bind("<Configure>", _draw_bar)
        self._prof_inner.after(60, _draw_bar)

        # ── Recent games ──────────────────────────────────────────────────────
        sep(self._prof_inner, padx=16, pady=4)
        tk.Label(self._prof_inner, text="RECENT GAMES",
                 font=("Georgia",9,"bold"), bg=CARD, fg=TXT2).pack(pady=(4,4))
        recent = self.app.dm.get_leaderboard(name=name)[:8]
        if not recent:
            tk.Label(self._prof_inner, text="No games on record.",
                     font=F_SMALL, bg=CARD, fg=TXT2).pack(pady=4)
            return
        for g in recent:
            res = g.get("result","")
            res_col = {"win": SUCC, "loss": DANG, "tie": WARN}.get(res, TXT)
            gr = tk.Frame(self._prof_inner, bg=CARD2, pady=5, padx=12)
            gr.pack(fill=tk.X, padx=16, pady=1)
            tk.Label(gr, text=res.upper(), font=("Georgia",9,"bold"),
                     bg=CARD2, fg=res_col, width=5, anchor="w").pack(side=tk.LEFT)
            tk.Label(gr, text=f"★{g.get('score',0):,}", font=F_SMALL,
                     bg=CARD2, fg=ACC).pack(side=tk.LEFT, padx=6)
            tk.Label(gr, text=g.get("diff","?"), font=F_SMALL,
                     bg=CARD2, fg=TXT2).pack(side=tk.RIGHT)
            tk.Label(gr, text=g.get("time",""), font=F_SMALL,
                     bg=CARD2, fg=TXT2).pack(side=tk.RIGHT, padx=8)


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN 6 ─ POST-GAME  (Charts + Stats + Piece-Dominance Line Chart)
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY SCREEN  ─  GitHub-style heatmap + streak tracker
# ═══════════════════════════════════════════════════════════════════════════════
class ActivityScreen(tk.Frame):
    CELL  = 13   # px per day square
    GAP   = 2    # px gap
    WEEKS = 26   # show last 26 weeks (~6 months)

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app       = app
        self._chart_cw = None
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=SURF, height=52)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📅  ACTIVITY & STREAKS",
                 font=F_TITLE, bg=SURF, fg=TXT).pack(side=tk.LEFT, padx=18)
        mkbtn(hdr, "◀  Back", lambda: self.app.show("start"),
              bg=CARD2, fg=TXT2, padx=14, pady=6, font=F_SMALL).pack(side=tk.RIGHT, padx=14)

        sep(self, pady=0)

        # Player selector
        sel = tk.Frame(self, bg=BG, pady=10)
        sel.pack(fill=tk.X, padx=20)
        tk.Label(sel, text="Player:", font=F_SMALL, bg=BG, fg=TXT2).pack(side=tk.LEFT)
        self._pvar = tk.StringVar()
        self._pcb  = ttk.Combobox(sel, textvariable=self._pvar,
                                   state="readonly", width=22, font=F_BODY)
        self._pcb.pack(side=tk.LEFT, padx=8)
        self._pcb.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        sep(self, pady=0)

        # Scrollable body
        body_outer = tk.Frame(self, bg=BG)
        body_outer.pack(fill=tk.BOTH, expand=True)
        body_outer.grid_rowconfigure(0, weight=1)
        body_outer.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(body_outer, bg=BG, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(body_outer, orient="vertical", command=self._canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=vsb.set)

        self._inner = tk.Frame(self._canvas, bg=BG)
        self._wid   = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._wid, width=e.width))
        self._canvas.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def on_show(self):
        names = self.app.dm.unique_names()
        self._pcb["values"] = names
        cur = self.app.player.get()
        self._pvar.set(cur if cur in names else (names[0] if names else ""))
        self._refresh()

    def _refresh(self):
        for w in self._inner.winfo_children():
            w.destroy()
        if self._chart_cw:
            try: self._chart_cw.get_tk_widget().destroy()
            except Exception: pass
            self._chart_cw = None

        name = self._pvar.get()
        if not name:
            tk.Label(self._inner, text="No player selected.",
                     font=F_BODY, bg=BG, fg=TXT2).pack(pady=40)
            return

        ps = self.app.dm.player_stats(name)
        if not ps:
            tk.Label(self._inner, text="No data for this player.",
                     font=F_BODY, bg=BG, fg=TXT2).pack(pady=40)
            return

        played  = ps.get("played", 0)
        wins    = ps.get("wins",   0)
        cur_s   = ps.get("current_streak", 0)
        best_s  = ps.get("best_streak",    0)
        daily   = ps.get("daily_games", {})

        # ── Streak cards ──────────────────────────────────────────────────────
        import datetime as dt
        sc_row = tk.Frame(self._inner, bg=BG)
        sc_row.pack(fill=tk.X, padx=20, pady=(16, 8))

        streak_fire = "🔥" * min(cur_s, 5) if cur_s else "─"
        for i, (icon, label, val, col) in enumerate([
            ("🔥", "Current Streak",
             f"{cur_s} win{'s' if cur_s!=1 else ''} {streak_fire}", WARN if cur_s else TXT2),
            ("🏆", "Best Streak",    f"{best_s} wins", ACC),
            ("🎮", "Total Played",   str(played),       TXT),
            ("✅", "Total Wins",     str(wins),          SUCC),
            ("📅", "Active Days",    str(len(daily)),    NEON),
        ]):
            c = tk.Frame(sc_row, bg=CARD2, padx=14, pady=14,
                         highlightthickness=1, highlightbackground=BDR)
            c.grid(row=0, column=i, padx=5, sticky="ew")
            sc_row.grid_columnconfigure(i, weight=1)
            tk.Label(c, text=icon, font=("Segoe UI Emoji", 20),
                     bg=CARD2, fg=col).pack()
            tk.Label(c, text=val,  font=("Georgia", 11, "bold"),
                     bg=CARD2, fg=col).pack(pady=(4, 0))
            tk.Label(c, text=label, font=("Georgia", 8),
                     bg=CARD2, fg=TXT2).pack()

        sep(self._inner, padx=20, pady=10)

        # ── Activity heatmap ──────────────────────────────────────────────────
        tk.Label(self._inner, text="CONTRIBUTION HEATMAP  (last 26 weeks)",
                 font=("Georgia", 9, "bold"), bg=BG, fg=TXT2).pack(
            anchor="w", padx=20, pady=(0, 6))

        # Build list of dates: today back WEEKS*7 days
        today       = dt.date.today()
        start_date  = today - dt.timedelta(weeks=self.WEEKS)
        # Align to Monday
        start_date -= dt.timedelta(days=start_date.weekday())

        # Colour scale: 0 games → dim, 1 → low, 2-3 → mid, 4+ → high
        def _day_col(d: dt.date):
            key = d.isoformat()
            if key not in daily:
                return "#1a1a2e"   # empty
            n = daily[key]["played"]
            w = daily[key]["wins"]
            if n == 0:  return "#1a1a2e"
            if w > 0:   # won at least one game today → green scale
                if n >= 4: return "#00c853"
                if n >= 2: return "#00963e"
                return       "#005c24"
            else:           # played but no wins → blue scale
                if n >= 4: return "#2979ff"
                if n >= 2: return "#1e4fc2"
                return       "#0d2a6e"

        C    = self.CELL
        G    = self.GAP
        # Day labels left margin
        LPAD = 28
        days_of_week  = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        total_cols    = self.WEEKS

        hm_h  = 7 * (C + G) + 20    # 7 rows + month label space
        hm_w  = total_cols * (C + G) + LPAD + 20

        hm = tk.Canvas(self._inner, bg=BG, width=hm_w, height=hm_h,
                       highlightthickness=0, bd=0)
        hm.pack(padx=20, pady=(0, 6))

        # Day-of-week labels
        for i, day_name in enumerate(days_of_week):
            if i % 2 == 0:   # only Mon/Wed/Fri/Sun to avoid clutter
                hm.create_text(LPAD - 4, i*(C+G) + C//2 + 2,
                               text=day_name[:1], anchor="e",
                               font=("Georgia", 7), fill=TXT2)

        # Draw cells
        cur = start_date
        for week in range(total_cols):
            # Month label at top of each week
            if cur.day <= 7:
                hm.create_text(LPAD + week*(C+G) + C//2, 0,
                               text=cur.strftime("%b"),
                               font=("Georgia", 7), fill=TXT2, anchor="n")
            for dow in range(7):
                d = cur + dt.timedelta(days=dow)
                if d > today:
                    break
                x = LPAD + week * (C + G)
                y = 14 + dow * (C + G)
                col = _day_col(d)
                rect_id = hm.create_rectangle(x, y, x+C, y+C,
                                               fill=col, outline="", tags=("day",))
                # Tooltip on hover
                key = d.isoformat()
                info = daily.get(key, {})
                tip  = (f"{d.strftime('%b %d, %Y')}\n"
                        f"{info.get('played',0)} game(s), "
                        f"{info.get('wins',0)} win(s)" if key in daily
                        else d.strftime('%b %d, %Y — no games'))
                def _enter(e, t=tip, rid=rect_id, c=col):
                    hm.itemconfig(rid, fill="#ffffff" if col != "#1a1a2e" else "#2a2a50")
                    self._tip_lbl.config(text=t)
                def _leave(e, rid=rect_id, c=col):
                    hm.itemconfig(rid, fill=c)
                    self._tip_lbl.config(text="")
                hm.tag_bind(rect_id, "<Enter>", _enter)
                hm.tag_bind(rect_id, "<Leave>", _leave)
            cur += dt.timedelta(weeks=1)

        # Legend
        leg = tk.Frame(self._inner, bg=BG)
        leg.pack(anchor="w", padx=22, pady=(2, 0))
        tk.Label(leg, text="Less", font=("Georgia", 8),
                 bg=BG, fg=TXT2).pack(side=tk.LEFT, padx=(0, 3))
        for col in ["#1a1a2e", "#005c24", "#00963e", "#00c853"]:
            tk.Frame(leg, bg=col, width=C, height=C).pack(side=tk.LEFT, padx=1)
        tk.Label(leg, text="More (wins)", font=("Georgia", 8),
                 bg=BG, fg=TXT2).pack(side=tk.LEFT, padx=(3, 12))
        for col in ["#0d2a6e", "#1e4fc2", "#2979ff"]:
            tk.Frame(leg, bg=col, width=C, height=C).pack(side=tk.LEFT, padx=1)
        tk.Label(leg, text="Games (no win)", font=("Georgia", 8),
                 bg=BG, fg=TXT2).pack(side=tk.LEFT, padx=(3, 0))

        # Hover tooltip label
        self._tip_lbl = tk.Label(self._inner, text="", font=F_SMALL,
                                  bg=CARD2, fg=TXT, padx=8, pady=4)
        self._tip_lbl.pack(anchor="w", padx=20, pady=(4, 0))

        sep(self._inner, padx=20, pady=10)

        # ── Win streak history chart ───────────────────────────────────────────
        if MPL and daily:
            tk.Label(self._inner,
                     text="DAILY GAMES (last 60 days)",
                     font=("Georgia", 9, "bold"),
                     bg=BG, fg=TXT2).pack(anchor="w", padx=20, pady=(0, 4))

            chart_wrap = tk.Frame(self._inner, bg=CARD)
            chart_wrap.pack(fill=tk.X, padx=20, pady=(0, 20))

            days_sorted = sorted(daily.keys())[-60:]
            dates_disp  = [dt.date.fromisoformat(d) for d in days_sorted]
            played_vals = [daily[d]["played"] for d in days_sorted]
            wins_vals   = [daily[d]["wins"]   for d in days_sorted]
            loss_vals   = [p - w for p, w in zip(played_vals, wins_vals)]

            fig = Figure(figsize=(6.5, 2.4), facecolor=CARD)
            ax  = fig.add_subplot(111)
            ax.set_facecolor(SURF)

            xs = range(len(dates_disp))
            ax.bar(xs, wins_vals,  color=SUCC, alpha=0.85, label="Wins",   linewidth=0)
            ax.bar(xs, loss_vals,  color=DANG, alpha=0.65, label="Losses",
                   bottom=wins_vals, linewidth=0)
            ax.set_title("Games Per Day", color=TXT, fontsize=8,
                         fontfamily="Georgia")
            ax.set_xticks(xs[::max(1, len(xs)//10)])
            ax.set_xticklabels(
                [dates_disp[i].strftime("%m/%d") for i in xs[::max(1, len(xs)//10)]],
                fontsize=6, color=TXT2)
            ax.legend(fontsize=7, facecolor=CARD, edgecolor=BDR, labelcolor=TXT)
            for sp in ax.spines.values(): sp.set_color(BDR)
            ax.tick_params(colors=TXT2, labelsize=7)
            ax.set_ylabel("Games", color=TXT2, fontsize=7)
            fig.tight_layout(pad=1.4)

            cw = FigureCanvasTkAgg(fig, master=chart_wrap)
            cw.draw()
            cw.get_tk_widget().pack(fill=tk.X)
            self._chart_cw = cw


# ═══════════════════════════════════════════════════════════════════════════════
# POST-GAME SCREEN
# ═══════════════════════════════════════════════════════════════════════════════
class PostGameScreen(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app         = app
        self._fig_cw     = None
        self._gif_job    = None
        self._gif_frames = []
        self._gif_idx    = 0
        self._gif_lbl    = None
        self._ov_bg      = None
        self._ov_card    = None
        self._piece_track = []
        self._build_skeleton()

    # ── Skeleton ──────────────────────────────────────────────────────────────
    def _build_skeleton(self):
        banner = tk.Frame(self, bg=SURF)
        banner.pack(fill=tk.X)
        txt_side = tk.Frame(banner, bg=SURF)
        txt_side.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=10)
        self._r_lbl = tk.Label(txt_side, text="", font=F_TITLE, bg=SURF, fg=TXT, anchor="w")
        self._r_lbl.pack(anchor="w")
        self._s_lbl = tk.Label(txt_side, text="", font=F_BODY, bg=SURF, fg=TXT2, anchor="w")
        self._s_lbl.pack(anchor="w", pady=(4,0))

        self._show_img_btn = mkbtn(banner, "🖼  View Result Image", self._reopen_overlay,
                                   bg=CARD2, fg=TXT2, padx=12, pady=7, font=F_SMALL)
        self._show_img_btn.pack(side=tk.RIGHT, padx=16, pady=12)
        self._show_img_btn.pack_forget()

        # Pack bottom buttons FIRST so expand=True content never pushes them off screen
        bot = tk.Frame(self, bg=SURF, pady=6)
        bot.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Frame(bot, bg=BDR, height=1).pack(fill=tk.X)
        btn_row = tk.Frame(bot, bg=SURF)
        btn_row.pack(pady=8)
        mkbtn(btn_row, "▶  Play Again",  self._play_again,
              bg=ACC, padx=22).pack(side=tk.LEFT, padx=(20, 6))
        mkbtn(btn_row, "🏠  Main Menu",  lambda: self.app.show("start"),
              bg=CARD2, fg=TXT2, padx=20).pack(side=tk.LEFT, padx=6)
        mkbtn(btn_row, "⚙  Difficulty", lambda: self.app.show("difficulty"),
              bg=CARD2, fg=TXT2, padx=20).pack(side=tk.LEFT, padx=6)

        # Content area fills remaining space above the buttons
        content = tk.Frame(self, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(10, 4))
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        self._chart_f = tk.Frame(content, bg=CARD)
        self._chart_f.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._stats_f = tk.Frame(content, bg=CARD)
        self._stats_f.grid(row=0, column=1, sticky="nsew")

    # ── on_show ───────────────────────────────────────────────────────────────
    def on_show(self, result="", msg="", bc=0, wc=0, final_score=0,
                time_str="", move_log=None, piece_track=None,
                corner_ctrl=0, best_flip=0, new_achievements=None):
        self._result      = result
        self._move_log    = move_log or []
        self._piece_track = piece_track or []
        self._corner_ctrl = corner_ctrl
        self._best_flip   = best_flip
        self._new_ach     = new_achievements or []

        col_map = {"win": SUCC, "loss": DANG, "tie": WARN}
        self._r_lbl.config(text=msg, fg=col_map.get(result, TXT))
        self._s_lbl.config(
            text=(f"Score: {final_score:,}   |   Time: {time_str}   |   "
                  f"You: {bc} pieces    AI: {wc} pieces"))

        has_img = result in self.app.images
        if has_img:
            self._show_img_btn.pack(side=tk.RIGHT, padx=16, pady=12)
        else:
            self._show_img_btn.pack_forget()

        for w in self._chart_f.winfo_children():
            w.destroy()
        for w in self._stats_f.winfo_children():
            w.destroy()
        if self._fig_cw:
            try: self._fig_cw.get_tk_widget().destroy()
            except Exception: pass
            self._fig_cw = None

        self._build_charts(bc, wc, self._move_log, self._piece_track)
        self._build_stats(bc, wc, final_score, time_str, self._move_log,
                          corner_ctrl, best_flip)
        self._last_overlay_args = (result, msg, bc, wc, final_score)
        self._show_overlay(result, msg, bc, wc, final_score)

        # Queue achievement toasts after overlay settles
        if self._new_ach:
            self.after(600, lambda: self._show_ach_toasts(list(self._new_ach)))

    # ── Charts (3 subplots) ───────────────────────────────────────────────────
    def _build_charts(self, bc, wc, log, piece_track):
        if not MPL:
            tk.Label(self._chart_f,
                     text="📊 Install matplotlib for charts:\npip install matplotlib",
                     font=F_BODY, bg=CARD, fg=TXT2).pack(expand=True)
            return
        if not log:
            tk.Label(self._chart_f, text="No move data to chart.",
                     font=F_BODY, bg=CARD, fg=TXT2).pack(expand=True)
            return

        fig = Figure(figsize=(6.2, 7.0), facecolor=CARD)

        # ── Subplot 1: Score Progression ──────────────────────────────────────
        ax1 = fig.add_subplot(311)
        ax1.set_facecolor(SURF)
        turns  = [m["turn"]  for m in log]
        scores = [m["score"] for m in log]
        py = [m["score"] for m in log if m["player"] != "AI"]
        px = [m["turn"]  for m in log if m["player"] != "AI"]
        ay = [m["score"] for m in log if m["player"] == "AI"]
        ax_x = [m["turn"] for m in log if m["player"] == "AI"]
        ax1.fill_between(turns, scores, alpha=0.08, color=NEON)
        ax1.plot(turns, scores, color=NEON, linewidth=1.2, alpha=0.5)
        ax1.scatter(px, py, color=SUCC, s=20, zorder=5, label="You", linewidths=0)
        ax1.scatter(ax_x, ay, color=DANG, s=20, zorder=5, label="AI", linewidths=0)
        ax1.axhline(0, color=BDR, linewidth=0.8, linestyle="--")
        ax1.set_title("Score Progression", color=TXT, fontsize=8, pad=3, fontfamily="Georgia")
        ax1.legend(fontsize=7, facecolor=CARD, edgecolor=BDR, labelcolor=TXT)
        for sp in ax1.spines.values(): sp.set_color(BDR)
        ax1.tick_params(colors=TXT2, labelsize=6)
        ax1.set_xlabel("Turn", color=TXT2, fontsize=6)
        ax1.set_ylabel("Score", color=TXT2, fontsize=6)

        # ── Subplot 2: Piece Count Bar ─────────────────────────────────────────
        ax2 = fig.add_subplot(312)
        ax2.set_facecolor(SURF)
        labels = ["You (⬛)", "AI (⬜)"]
        vals   = [bc, wc]
        clrs   = [SUCC, DANG] if bc >= wc else [DANG, SUCC]
        bars   = ax2.bar(labels, vals, color=clrs, edgecolor=BDR, linewidth=0.6, width=0.45)
        ax2.set_title("Final Piece Count", color=TXT, fontsize=8, pad=3, fontfamily="Georgia")
        for sp in ax2.spines.values(): sp.set_color(BDR)
        ax2.tick_params(colors=TXT2, labelsize=7)
        ax2.set_ylabel("Pieces", color=TXT2, fontsize=6)
        for bar, v in zip(bars, vals):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                     str(v), ha="center", va="bottom", color=TXT, fontsize=8)

        # ── Subplot 3: Piece Dominance Line Chart ─────────────────────────────
        ax3 = fig.add_subplot(313)
        ax3.set_facecolor(SURF)
        if piece_track and len(piece_track) >= 2:
            pt_turns = [t for t, b, w in piece_track]
            pt_black = [b for t, b, w in piece_track]
            pt_white = [w for t, b, w in piece_track]
            ax3.plot(pt_turns, pt_black, color=SUCC, linewidth=1.5,
                     label="You (⬛)", marker="o", markersize=2)
            ax3.plot(pt_turns, pt_white, color=DANG, linewidth=1.5,
                     label="AI (⬜)",  marker="o", markersize=2)
            ax3.fill_between(pt_turns, pt_black, pt_white,
                             where=[b > w for b, w in zip(pt_black, pt_white)],
                             alpha=0.15, color=SUCC, label="_nolegend_")
            ax3.fill_between(pt_turns, pt_black, pt_white,
                             where=[b <= w for b, w in zip(pt_black, pt_white)],
                             alpha=0.15, color=DANG, label="_nolegend_")
            ax3.axhline(32, color=BDR, linewidth=0.7, linestyle="--", alpha=0.5)
            ax3.set_title("Piece Dominance Over Time", color=TXT, fontsize=8,
                          pad=3, fontfamily="Georgia")
            ax3.legend(fontsize=7, facecolor=CARD, edgecolor=BDR, labelcolor=TXT)
        else:
            ax3.text(0.5, 0.5, "No piece-track data", ha="center", va="center",
                     color=TXT2, fontsize=8, transform=ax3.transAxes)
            ax3.set_title("Piece Dominance Over Time", color=TXT, fontsize=8,
                          pad=3, fontfamily="Georgia")
        for sp in ax3.spines.values(): sp.set_color(BDR)
        ax3.tick_params(colors=TXT2, labelsize=6)
        ax3.set_xlabel("Turn", color=TXT2, fontsize=6)
        ax3.set_ylabel("Pieces", color=TXT2, fontsize=6)

        fig.tight_layout(pad=2.0)
        cw = FigureCanvasTkAgg(fig, master=self._chart_f)
        cw.draw()
        cw.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._fig_cw = cw

    # ── Stats panel (scrollable) ───────────────────────────────────────────────
    def _build_stats(self, bc, wc, final_score, time_str, log,
                     corner_ctrl, best_flip):
        outer = self._stats_f

        # ── Scrollable canvas wrapper ─────────────────────────────────────────
        canvas = tk.Canvas(outer, bg=CARD, highlightthickness=0, bd=0)
        vsb    = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        p = tk.Frame(canvas, bg=CARD)
        win_id = canvas.create_window((0, 0), window=p, anchor="nw")

        def _on_frame_conf(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_conf(e):
            canvas.itemconfig(win_id, width=e.width)
        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        p.bind("<Configure>", _on_frame_conf)
        canvas.bind("<Configure>", _on_canvas_conf)
        canvas.bind("<MouseWheel>", _scroll)
        p.bind("<MouseWheel>", _scroll)

        # ── Content ───────────────────────────────────────────────────────────
        tk.Label(p, text="MATCH STATS", font=F_HEAD, bg=CARD, fg=NEON).pack(pady=(16, 8))

        pm = [m for m in log if m["player"] != "AI"]
        am = [m for m in log if m["player"] == "AI"]
        avg_t  = sum(m["time"]    for m in pm) / len(pm) if pm else 0
        flip_y = sum(m["flipped"] for m in pm)
        flip_a = sum(m["flipped"] for m in am)
        best_d = max((m["delta"]  for m in pm), default=0)

        def _row(label, val, col, parent=p):
            r = tk.Frame(parent, bg=CARD2, pady=7, padx=12)
            r.pack(fill=tk.X, padx=10, pady=2)
            r.bind("<MouseWheel>", _scroll)
            tk.Label(r, text=label, font=F_SMALL, bg=CARD2, fg=TXT2,
                     anchor="w").pack(side=tk.LEFT)
            tk.Label(r, text=val,   font=F_SMALL, bg=CARD2, fg=col,
                     anchor="e").pack(side=tk.RIGHT)

        _row("Your Pieces",    str(bc),             SUCC if bc > wc else TXT)
        _row("AI Pieces",      str(wc),             SUCC if wc > bc else TXT)
        _row("Final Score",    f"{final_score:,}",  ACC)
        _row("Time Played",    time_str,             TXT)
        _row("Total Turns",    str(len(log)),        TXT)
        _row("Avg Move Time",  f"{avg_t:.1f}s",      WARN)
        _row("Flipped by You", str(flip_y),          SUCC)
        _row("Flipped by AI",  str(flip_a),          DANG)
        _row("Best Move (Δ)",  f"+{best_d:,}",       ACC)

        # ── ADVANCED section ──────────────────────────────────────────────────
        sep(p, padx=10, pady=6, color=ACC2)
        tk.Label(p, text="ADVANCED", font=("Georgia", 9, "bold"),
                 bg=CARD, fg=TXT2).pack(pady=(0, 4))
        _row("Corners Held",    f"{corner_ctrl} / 4",  NEON)
        _row("Best Flip Combo", f"{best_flip} pieces",  HINT_COL)

        # ── Diff breakdown ────────────────────────────────────────────────────
        sep(p, padx=10, pady=4, color=BDR)
        tk.Label(p, text="WIN RATE BY DIFFICULTY",
                 font=("Georgia", 8, "bold"), bg=CARD, fg=TXT2).pack(pady=(0, 4))
        name = self.app.player.get()
        ps   = self.app.dm.player_stats(name)
        if ps:
            ds = ps.get("diff_stats", {})
            for diff, col in [("Easy", SUCC), ("Medium", WARN), ("Hard", DANG)]:
                d = ds.get(diff, {"played": 0, "wins": 0})
                if d["played"]:
                    dwr = f"{d['wins']/d['played']*100:.0f}%  ({d['wins']}/{d['played']})"
                else:
                    dwr = "—"
                _row(f"{diff}", dwr, col)

        # ── Personal best badge ───────────────────────────────────────────────
        if ps and final_score > 0 and final_score >= ps.get("high_score", 0):
            sep(p, padx=10, pady=6, color=WARN)
            tk.Label(p, text="🌟 NEW PERSONAL BEST!",
                     font=F_HEAD, bg=CARD, fg=WARN).pack()

        # ── Your record ───────────────────────────────────────────────────────
        sep(p, padx=10, pady=8)
        tk.Label(p, text="YOUR RECORD",
                 font=("Georgia", 9, "bold"), bg=CARD, fg=TXT2).pack()
        if ps and ps["played"]:
            wr = f"{ps['wins']/ps['played']*100:.0f}%"
            tk.Label(p,
                     text=(f"W {ps['wins']}  L {ps['losses']}  T {ps['ties']}\n"
                           f"Win Rate: {wr}   Best: {ps['high_score']:,}"),
                     font=F_SMALL, bg=CARD, fg=TXT2,
                     justify=tk.CENTER).pack(pady=(4, 12))

    # ── Overlay (result popup + mini piece-dominance chart) ───────────────────
    def _show_overlay(self, result, msg, bc, wc, final_score):
        self._close_overlay()
        col_map  = {"win": SUCC, "loss": DANG, "tie": WARN}
        acc_col  = col_map.get(result, TXT)
        img_key  = result if result in ("win","loss","tie") else None
        first_img= self.app.images.get(img_key) if img_key else None
        frames   = self.app.images.get(f"{img_key}_frames", []) if img_key else []
        emoji    = {"win":"🎉","loss":"😢","tie":"🤝"}.get(result,"")

        backdrop = tk.Frame(self, bg="#05050f")
        backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)
        backdrop.bind("<Button-1>", lambda e: self._close_overlay())
        self._ov_bg = backdrop

        card = tk.Frame(backdrop, bg=CARD,
                        highlightthickness=2, highlightbackground=acc_col)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.bind("<Button-1>", lambda e: "break")
        self._ov_card = card

        tk.Frame(card, bg=acc_col, height=4).pack(fill=tk.X)
        inner = tk.Frame(card, bg=CARD, padx=36, pady=20)
        inner.pack()

        if first_img:
            img_lbl = tk.Label(inner, image=first_img, bg=CARD, cursor="arrow", bd=0)
            img_lbl._img_ref = first_img
            img_lbl.pack()
            self._gif_lbl = img_lbl
            if len(frames) > 1:
                self._gif_frames = frames
                self._gif_idx    = 0
                self._gif_job    = self.after(80, self._tick_gif)
        else:
            tk.Label(inner, text=emoji, font=("Segoe UI Emoji", 72), bg=CARD).pack(pady=(8,0))

        tk.Label(inner, text=msg, font=F_TITLE, bg=CARD, fg=acc_col).pack(pady=(14,4))

        summary = tk.Frame(inner, bg=CARD2, padx=20, pady=10)
        summary.pack(fill=tk.X, pady=(6,0))
        for txt, col in [
            (f"⬛ You — {bc} pieces", SUCC if bc > wc else TXT),
            (f"⬜ AI  — {wc} pieces", SUCC if wc > bc else TXT),
            (f"Score: {final_score:,}", ACC),
        ]:
            tk.Label(summary, text=txt, font=F_MONO, bg=CARD2, fg=col).pack(anchor="w", pady=1)

        # ── Mini piece-dominance line chart inside overlay (if MPL) ───────────
        if MPL and self._piece_track and len(self._piece_track) >= 2:
            chart_frame = tk.Frame(inner, bg=CARD, pady=4)
            chart_frame.pack(fill=tk.X, pady=(10, 0))
            try:
                fig_m = Figure(figsize=(4.2, 1.6), facecolor=CARD)
                ax_m  = fig_m.add_subplot(111)
                ax_m.set_facecolor(SURF)
                pt = self._piece_track
                xs = [t for t, b, w in pt]
                yb = [b for t, b, w in pt]
                yw = [w for t, b, w in pt]
                ax_m.plot(xs, yb, color=SUCC, linewidth=1.2, label="You")
                ax_m.plot(xs, yw, color=DANG, linewidth=1.2, label="AI")
                ax_m.fill_between(xs, yb, yw,
                                  where=[b > w for b, w in zip(yb, yw)],
                                  alpha=0.15, color=SUCC)
                ax_m.fill_between(xs, yb, yw,
                                  where=[b <= w for b, w in zip(yb, yw)],
                                  alpha=0.15, color=DANG)
                ax_m.set_title("Piece Dominance", color=TXT, fontsize=7,
                               fontfamily="Georgia", pad=2)
                ax_m.legend(fontsize=6, facecolor=CARD, edgecolor=BDR, labelcolor=TXT)
                for sp in ax_m.spines.values(): sp.set_color(BDR)
                ax_m.tick_params(colors=TXT2, labelsize=5)
                fig_m.tight_layout(pad=1.0)
                cw_m = FigureCanvasTkAgg(fig_m, master=chart_frame)
                cw_m.draw()
                cw_m.get_tk_widget().pack(fill=tk.X)
            except Exception:
                pass

        sep_line = tk.Frame(inner, bg=BDR, height=1)
        sep_line.pack(fill=tk.X, pady=(16,0))

        # Achievements unlocked this game (if any)
        if hasattr(self, "_new_ach") and self._new_ach:
            self._add_ach_to_overlay(inner, self._new_ach)
            sep_line2 = tk.Frame(inner, bg=BDR, height=1)
            sep_line2.pack(fill=tk.X, pady=(8, 0))

        btn_row = tk.Frame(inner, bg=CARD)
        btn_row.pack(fill=tk.X, pady=(10,0))
        mkbtn(btn_row, "✕  Close", self._close_overlay,
              bg=CARD2, fg=TXT2, padx=16, pady=8).pack(side=tk.LEFT)
        mkbtn(btn_row, "▶  Play Again", self._play_again,
              bg=ACC, padx=16, pady=8).pack(side=tk.RIGHT)
        tk.Label(inner, text="Click outside the card or press Esc to close",
                 font=F_SMALL, bg=CARD, fg=TXT2).pack(pady=(8,0))
        self.app.bind("<Escape>", lambda e: self._close_overlay())
        self._animate_popup(card, step=0)

    def _animate_popup(self, card, step):
        steps = 6
        if step <= steps:
            pad = int(40 * (1 - step / steps))
            card.config(padx=0, pady=0)
            inner_frames = [w for w in card.winfo_children()
                            if isinstance(w, tk.Frame) and w.winfo_exists()]
            if inner_frames:
                inner_frames[-1].config(padx=max(4, 36-pad), pady=max(2, 20-pad//2))
            self.after(18, self._animate_popup, card, step+1)

    def _close_overlay(self):
        if self._gif_job:
            try: self.after_cancel(self._gif_job)
            except Exception: pass
        self._gif_job = None; self._gif_frames = []; self._gif_idx = 0; self._gif_lbl = None
        try:
            self.app.unbind("<Escape>")
            self.app.bind("<Escape>", lambda e: self.app.attributes("-fullscreen", False))
        except Exception:
            pass
        if self._ov_bg and self._ov_bg.winfo_exists():
            self._ov_bg.destroy()
        self._ov_bg = None; self._ov_card = None

    def _reopen_overlay(self):
        if hasattr(self, "_last_overlay_args"):
            self._show_overlay(*self._last_overlay_args)

    def _tick_gif(self):
        if not self._gif_frames or not self._gif_lbl: return
        if not self._gif_lbl.winfo_exists(): return
        self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)
        frame = self._gif_frames[self._gif_idx]
        self._gif_lbl.config(image=frame)
        self._gif_lbl._img_ref = frame
        self._gif_job = self.after(80, self._tick_gif)

    def _play_again(self):
        self.app.show("game")

    # ── Achievement toasts (slide-in banners) ─────────────────────────────────
    def _show_ach_toasts(self, ids: list, delay=0):
        if not ids:
            return
        aid  = ids[0]
        rest = ids[1:]
        info = ACHIEVEMENTS.get(aid)
        if not info:
            self._show_ach_toasts(rest, delay); return

        icon, title, desc, rarity = info
        rar_col = {"Legendary": "#ffd700", "Rare": ACC, "Common": NEON}.get(rarity, TXT)

        toast = tk.Frame(self, bg=CARD2,
                         highlightthickness=2, highlightbackground=rar_col)
        toast.place(relx=1.0, rely=0.06, anchor="ne")   # starts off-screen right

        tk.Frame(toast, bg=rar_col, width=4).pack(side=tk.LEFT, fill=tk.Y)
        inner = tk.Frame(toast, bg=CARD2, padx=12, pady=10)
        inner.pack(side=tk.LEFT)
        tk.Label(inner, text="🏆 ACHIEVEMENT UNLOCKED",
                 font=("Georgia", 8, "bold"), bg=CARD2, fg=rar_col).pack(anchor="w")
        tk.Label(inner, text=f"{icon}  {title}",
                 font=("Georgia", 11, "bold"), bg=CARD2, fg=TXT).pack(anchor="w")
        tk.Label(inner, text=desc, font=F_SMALL, bg=CARD2, fg=TXT2).pack(anchor="w")
        tk.Label(inner, text=rarity.upper(),
                 font=("Georgia", 8), bg=CARD2, fg=rar_col).pack(anchor="w")

        # Slide in
        def _slide_in(step=0):
            if not toast.winfo_exists(): return
            target = 1.0 - 0.01 * step
            toast.place(relx=max(0.72, target), rely=0.06, anchor="ne")
            if target > 0.72:
                self.after(14, _slide_in, step + 1)
            else:
                # Hold for 2.8 s then slide out
                self.after(2800, _slide_out)

        def _slide_out(step=0):
            if not toast.winfo_exists(): return
            target = 0.72 + 0.03 * step
            toast.place(relx=min(1.05, target), rely=0.06, anchor="ne")
            if target < 1.05:
                self.after(14, _slide_out, step + 1)
            else:
                toast.destroy()
                # Show next toast with small gap
                self.after(200, self._show_ach_toasts, rest)

        self.after(delay, _slide_in)

    # ── Add achievements badge list inside overlay ─────────────────────────────
    def _add_ach_to_overlay(self, inner, new_ach):
        if not new_ach:
            return
        sep_line = tk.Frame(inner, bg=BDR, height=1)
        sep_line.pack(fill=tk.X, pady=(10, 6))
        tk.Label(inner, text="🏆  ACHIEVEMENTS UNLOCKED",
                 font=("Georgia", 9, "bold"), bg=CARD, fg=WARN).pack()
        for aid in new_ach:
            info = ACHIEVEMENTS.get(aid)
            if not info: continue
            icon, title, desc, rarity = info
            rar_col = {"Legendary": "#ffd700", "Rare": ACC, "Common": NEON}.get(rarity, TXT)
            ab = tk.Frame(inner, bg=CARD2, padx=10, pady=6)
            ab.pack(fill=tk.X, pady=2)
            tk.Label(ab, text=f"{icon}  {title}",
                     font=("Georgia", 10, "bold"), bg=CARD2, fg=rar_col).pack(side=tk.LEFT)
            tk.Label(ab, text=rarity, font=F_SMALL, bg=CARD2, fg=TXT2).pack(side=tk.RIGHT)


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN 7 ─ ACHIEVEMENTS / TROPHIES
# ═══════════════════════════════════════════════════════════════════════════════
class AchievementsScreen(tk.Frame):
    RARITY_ORDER = {"Legendary": 0, "Rare": 1, "Common": 2}

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        # Header bar
        hdr = tk.Frame(self, bg=SURF, height=54)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🏆  TROPHIES & ACHIEVEMENTS",
                 font=F_TITLE, bg=SURF, fg=TXT).pack(side=tk.LEFT, padx=18)
        mkbtn(hdr, "◀  Back", lambda: self.app.show("start"),
              bg=CARD2, fg=TXT2, padx=14, pady=6,
              font=F_SMALL).pack(side=tk.RIGHT, padx=14)
        sep(self, pady=0)

        # Player selector
        top = tk.Frame(self, bg=BG, pady=10)
        top.pack(fill=tk.X, padx=20)
        tk.Label(top, text="Viewing:", font=F_SMALL, bg=BG, fg=TXT2).pack(side=tk.LEFT)
        self._pvar = tk.StringVar()
        self._pcb  = ttk.Combobox(top, textvariable=self._pvar,
                                   state="readonly", width=22, font=F_BODY)
        self._pcb.pack(side=tk.LEFT, padx=8)
        self._pcb.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        # Progress label
        self._prog_lbl = tk.Label(top, text="", font=F_MONO, bg=BG, fg=NEON)
        self._prog_lbl.pack(side=tk.RIGHT)

        sep(self, pady=0)

        # Scrollable grid
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self._canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=vsb.set)

        self._grid_frame = tk.Frame(self._canvas, bg=BG)
        self._win_id = self._canvas.create_window(
            (0, 0), window=self._grid_frame, anchor="nw")

        self._grid_frame.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._win_id, width=e.width))
        self._canvas.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._grid_frame.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def on_show(self):
        names = self.app.dm.unique_names()
        self._pcb["values"] = names
        cur = self.app.player.get()
        self._pvar.set(cur if cur in names else (names[0] if names else ""))
        self._refresh()

    def _refresh(self):
        for w in self._grid_frame.winfo_children():
            w.destroy()

        name    = self._pvar.get()
        unlocked = set(self.app.dm.get_achievements(name))
        total    = len(ACHIEVEMENTS)
        got      = len(unlocked)

        self._prog_lbl.config(
            text=f"{got} / {total}  ({got/total*100:.0f}%)" if total else "")

        # Sort: unlocked first, then by rarity
        def sort_key(aid):
            _, _, _, rarity = ACHIEVEMENTS[aid]
            locked = 0 if aid in unlocked else 1
            return (locked, self.RARITY_ORDER.get(rarity, 9))

        aids = sorted(ACHIEVEMENTS.keys(), key=sort_key)
        COLS = 2

        for i, aid in enumerate(aids):
            icon, title, desc, rarity = ACHIEVEMENTS[aid]
            is_unlocked = aid in unlocked
            rar_col = {"Legendary": "#ffd700", "Rare": ACC, "Common": NEON}.get(rarity, TXT)
            bg_col  = CARD if is_unlocked else SURF
            fg_col  = TXT  if is_unlocked else TXT2
            bdr_col = rar_col if is_unlocked else BDR

            card = tk.Frame(self._grid_frame, bg=bg_col,
                            highlightthickness=1, highlightbackground=bdr_col,
                            padx=0, pady=0)
            card.grid(row=i // COLS, column=i % COLS,
                      padx=10, pady=8, sticky="nsew")
            self._grid_frame.grid_columnconfigure(i % COLS, weight=1)
            card.bind("<MouseWheel>",
                lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

            # Accent bar
            tk.Frame(card, bg=bdr_col, height=3).pack(fill=tk.X)

            body = tk.Frame(card, bg=bg_col, padx=16, pady=14)
            body.pack(fill=tk.BOTH, expand=True)
            body.bind("<MouseWheel>",
                lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

            # Icon + lock
            icon_row = tk.Frame(body, bg=bg_col)
            icon_row.pack(anchor="w")
            disp_icon = icon if is_unlocked else "🔒"
            tk.Label(icon_row, text=disp_icon,
                     font=("Segoe UI Emoji", 26), bg=bg_col,
                     fg=rar_col if is_unlocked else TXT2).pack(side=tk.LEFT)
            rar_lbl = tk.Label(icon_row, text=f"  {rarity.upper()}",
                               font=("Georgia", 8, "bold"),
                               bg=bg_col, fg=rar_col if is_unlocked else TXT2)
            rar_lbl.pack(side=tk.LEFT, padx=(6, 0))

            # Title
            title_disp = title if is_unlocked else "???"
            tk.Label(body, text=title_disp,
                     font=("Georgia", 11, "bold"),
                     bg=bg_col, fg=fg_col, anchor="w").pack(anchor="w", pady=(6, 2))

            # Description
            desc_disp = desc if is_unlocked else "Keep playing to unlock…"
            tk.Label(body, text=desc_disp,
                     font=F_SMALL, bg=bg_col, fg=TXT2,
                     anchor="w", wraplength=230, justify=tk.LEFT).pack(anchor="w")

            # Unlocked badge
            if is_unlocked:
                tk.Label(body, text="✔ UNLOCKED",
                         font=("Georgia", 8, "bold"),
                         bg=bg_col, fg=SUCC).pack(anchor="e", pady=(8, 0))


# ═══════════════════════════════════════════════════════════════════════════════
# SPECTATOR SCREEN  ─  AI vs AI (dedicated full screen)
# ═══════════════════════════════════════════════════════════════════════════════
class SpectatorScreen(tk.Frame):
    """Full-screen AI vs AI battle screen."""

    DIFF_PAIRS = [
        ("Easy",   "Easy"),
        ("Easy",   "Medium"),
        ("Easy",   "Hard"),
        ("Medium", "Medium"),
        ("Medium", "Hard"),
        ("Hard",   "Hard"),
    ]

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app       = app
        self._running  = False
        self._job      = None
        self._board    = []
        self._cur      = BLACK
        self._scores   = {BLACK: 0, WHITE: 0}
        self._turn     = 0
        self._speed    = 700    # ms between moves
        self._d_black  = "Easy"
        self._d_white  = "Hard"
        self._piece_track = []
        self._fig_cw   = None
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=SURF, height=52)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🤖 AI vs AI SPECTATOR",
                 font=F_TITLE, bg=SURF, fg=TXT).pack(side=tk.LEFT, padx=16)
        mkbtn(hdr, "◀  Back", lambda: self._back(),
              bg=CARD2, fg=TXT2, padx=14, pady=6, font=F_SMALL).pack(side=tk.RIGHT, padx=14)

        sep(self, pady=0)

        # Controls bar
        ctrl = tk.Frame(self, bg=CARD2, pady=7)
        ctrl.pack(fill=tk.X, padx=0)

        tk.Label(ctrl, text="⬛ BLACK:", font=F_SMALL, bg=CARD2, fg=TXT2).pack(side=tk.LEFT, padx=(14,3))
        self._cb_black = ttk.Combobox(ctrl, values=["Easy","Medium","Hard"],
                                       state="readonly", width=8, font=F_SMALL)
        self._cb_black.set("Easy")
        self._cb_black.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(ctrl, text="⬜ WHITE:", font=F_SMALL, bg=CARD2, fg=TXT2).pack(side=tk.LEFT, padx=(0,3))
        self._cb_white = ttk.Combobox(ctrl, values=["Easy","Medium","Hard"],
                                       state="readonly", width=8, font=F_SMALL)
        self._cb_white.set("Hard")
        self._cb_white.pack(side=tk.LEFT, padx=(0, 14))

        sep(ctrl, orient="v", padx=4)

        tk.Label(ctrl, text="Speed:", font=F_SMALL, bg=CARD2, fg=TXT2).pack(side=tk.LEFT, padx=(6,3))
        self._speed_var = tk.IntVar(value=700)
        speed_map = {"Slow": 1200, "Normal": 700, "Fast": 300, "Turbo": 80}
        for label, ms in speed_map.items():
            col = NEON if label == "Normal" else TXT2
            mkbtn(ctrl, label,
                  lambda m=ms: self._set_speed(m),
                  bg=CARD2, fg=col, padx=7, pady=3, font=F_SMALL).pack(side=tk.LEFT, padx=1)

        sep(ctrl, orient="v", padx=8)

        self._play_btn = mkbtn(ctrl, "▶ Start", self._toggle_play,
                               bg=SUCC, fg=BG, padx=12, pady=3, font=F_SMALL)
        self._play_btn.pack(side=tk.LEFT, padx=4)
        mkbtn(ctrl, "↺ Restart", self._restart,
              bg=CARD, fg=WARN, padx=10, pady=3, font=F_SMALL).pack(side=tk.LEFT, padx=3)

        # Win counter
        self._win_lbl = tk.Label(ctrl, text="", font=F_MONO, bg=CARD2, fg=TXT)
        self._win_lbl.pack(side=tk.RIGHT, padx=16)

        # Main body
        body = tk.Frame(self, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Board panel (left)
        board_wrap = tk.Frame(body, bg=BG)
        board_wrap.grid(row=0, column=0, padx=20, pady=10)

        cs = CELL_SIZE * BOARD_SIZE
        self._canvas = tk.Canvas(board_wrap, width=cs, height=cs,
                                  bg=BOARD_BG,
                                  highlightthickness=2, highlightbackground=BDR)
        self._canvas.pack()

        # Piece count bar under board
        cnt_row = tk.Frame(board_wrap, bg=BG)
        cnt_row.pack(fill=tk.X, pady=(6,0))
        self._lbl_b = tk.Label(cnt_row, text="⬛ Black: 2",
                                font=F_BODY, bg=BG, fg=TXT)
        self._lbl_b.pack(side=tk.LEFT)
        self._lbl_w = tk.Label(cnt_row, text="⬜ White: 2",
                                font=F_BODY, bg=BG, fg=TXT)
        self._lbl_w.pack(side=tk.RIGHT)

        self._lbl_turn = tk.Label(board_wrap, text="Press ▶ Start",
                                   font=F_HEAD, bg=BG, fg=TXT2)
        self._lbl_turn.pack(pady=(4, 0))

        # Right panel – live chart
        right = tk.Frame(body, bg=CARD)
        right.grid(row=0, column=1, sticky="nsew", padx=(0,16), pady=10)
        tk.Label(right, text="PIECE DOMINANCE",
                 font=("Georgia", 9, "bold"), bg=CARD, fg=TXT2).pack(pady=(12,4))
        self._chart_frame = tk.Frame(right, bg=CARD)
        self._chart_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,10))

        # Move log
        tk.Label(right, text="MOVE LOG",
                 font=("Georgia", 9, "bold"), bg=CARD, fg=TXT2).pack(pady=(0,2))
        self._log = tk.Text(right, height=5, font=("Georgia", 9),
                             bg=CARD2, fg=TXT2, relief=tk.FLAT, bd=0,
                             state=tk.DISABLED, wrap=tk.NONE,
                             highlightthickness=0)
        self._log.pack(fill=tk.X, padx=8, pady=(0,10))

    # ── Controls ──────────────────────────────────────────────────────────────
    def on_show(self):
        self._wins = {BLACK: 0, WHITE: 0}
        self._update_win_counter()
        self._reset_board()
        self._draw_board()

    def _back(self):
        self._stop()
        self.app.show("start")

    def _set_speed(self, ms):
        self._speed = ms
        # Restart loop at new speed if already running
        if self._running and self._job:
            self.after_cancel(self._job)
            self._job = self.after(self._speed, self._step)

    def _toggle_play(self):
        if self._running:
            self._stop()
        else:
            self._d_black = self._cb_black.get()
            self._d_white = self._cb_white.get()
            self._running = True
            self._play_btn.config(text="⏸ Pause", bg=WARN)
            self._job = self.after(self._speed, self._step)

    def _stop(self):
        self._running = False
        self._play_btn.config(text="▶ Start", bg=SUCC)
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def _restart(self):
        self._stop()
        self._reset_board()
        self._draw_board()

    def _reset_board(self):
        self._board = [[EMPTY]*BOARD_SIZE for _ in range(BOARD_SIZE)]
        self._board[3][3] = self._board[4][4] = WHITE
        self._board[3][4] = self._board[4][3] = BLACK
        self._cur   = BLACK
        self._turn  = 0
        self._piece_track = []
        self._snapshot()
        self._log.config(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.config(state=tk.DISABLED)
        self._lbl_turn.config(text="Press ▶ Start", fg=TXT2)
        self._rebuild_chart()

    def _snapshot(self):
        bc = sum(row.count(BLACK) for row in self._board)
        wc = sum(row.count(WHITE) for row in self._board)
        self._piece_track.append((self._turn, bc, wc))

    # ── One game step (one AI move) ───────────────────────────────────────────
    def _step(self):
        if not self._running:
            return
        moves = valid_moves(self._board, self._cur)
        if not moves:
            opp = WHITE if self._cur == BLACK else BLACK
            if not valid_moves(self._board, opp):
                self._game_over()
                return
            self._cur = opp
            self._job = self.after(self._speed, self._step)
            return

        diff  = self._d_black if self._cur == BLACK else self._d_white
        model = None
        if diff == "Medium":
            model = self.app.ml_med if self.app.ml_med.ok else None
            if model:
                is_max = (self._cur == WHITE)
                _, mv  = minimax(self._board, 1, float("-inf"), float("inf"), is_max, model)
                best   = mv if mv else random.choice(moves)
            else:
                best = max(moves, key=lambda rc: (
                    sum(r in (0,7) or c in (0,7) for r,c in [rc]),
                    HMAP[rc[0]][rc[1]]))
        elif diff == "Hard":
            model = self.app.ml_hard if self.app.ml_hard.ok else None
            is_max = (self._cur == WHITE)
            _, mv  = minimax(self._board, 3, float("-inf"), float("inf"), is_max, model)
            best   = mv if mv else random.choice(moves)
        else:
            best = random.choice(moves)

        flipped = apply_move(self._board, self._cur, best[0], best[1])
        self._turn += 1
        self._snapshot()

        # log entry
        player_name = f"⬛ {self._d_black}" if self._cur == BLACK else f"⬜ {self._d_white}"
        self._log_move(player_name, best, len(flipped))

        self._cur = WHITE if self._cur == BLACK else BLACK
        self._draw_board()
        self._update_chart()
        self._job = self.after(self._speed, self._step)

    def _log_move(self, name, pos, flipped):
        cols = "abcdefghijkl"
        cell = f"{cols[pos[1]]}{pos[0]+1}"
        line = f"T{self._turn:02d}  {name}  {cell}  (+{flipped} flips)\n"
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, line)
        self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)

    def _game_over(self):
        self._stop()
        bc = sum(row.count(BLACK) for row in self._board)
        wc = sum(row.count(WHITE) for row in self._board)
        if bc > wc:
            winner = BLACK
            msg = f"⬛ {self._d_black} WINS!  ({bc} vs {wc})"
            col = SUCC
        elif wc > bc:
            winner = WHITE
            msg = f"⬜ {self._d_white} WINS!  ({wc} vs {bc})"
            col = DANG
        else:
            winner = None
            msg = f"DRAW!  ({bc} each)"
            col = WARN
        if winner is not None:
            self._wins[winner] = self._wins.get(winner, 0) + 1
        self._update_win_counter()
        self._lbl_turn.config(text=msg, fg=col)
        # Auto-restart after 3 s if continuous watch
        self._job = self.after(3000, self._auto_next)

    def _auto_next(self):
        if not self._running:
            self._reset_board()
            self._draw_board()
            self._d_black = self._cb_black.get()
            self._d_white = self._cb_white.get()
            self._running = True
            self._play_btn.config(text="⏸ Pause", bg=WARN)
            self._job = self.after(self._speed, self._step)

    def _update_win_counter(self):
        wb = self._wins.get(BLACK, 0)
        ww = self._wins.get(WHITE, 0)
        self._win_lbl.config(
            text=f"⬛ {self._d_black} {wb} — {ww} {self._d_white} ⬜")

    # ── Board drawing ─────────────────────────────────────────────────────────
    def _draw_board(self):
        c = self._canvas
        c.delete("all")

        # Grid lines
        for i in range(BOARD_SIZE + 1):
            c.create_line(i*CELL_SIZE, 0, i*CELL_SIZE, BOARD_SIZE*CELL_SIZE,
                          fill=BOARD_LN, width=1)
            c.create_line(0, i*CELL_SIZE, BOARD_SIZE*CELL_SIZE, i*CELL_SIZE,
                          fill=BOARD_LN, width=1)
        # Star dots
        for dr, dc in [(2,2),(2,5),(5,2),(5,5)]:
            cx = dc*CELL_SIZE + CELL_SIZE//2
            cy = dr*CELL_SIZE + CELL_SIZE//2
            c.create_oval(cx-4, cy-4, cx+4, cy+4, fill=BOARD_LN, outline="")

        bc = wc = 0
        for r in range(BOARD_SIZE):
            for cc in range(BOARD_SIZE):
                cx = cc*CELL_SIZE + CELL_SIZE//2
                cy = r*CELL_SIZE  + CELL_SIZE//2
                p  = CELL_SIZE//2 - 5
                v  = self._board[r][cc]
                if v == BLACK:
                    bc += 1
                    # Black Hole with purple glow
                    c.create_oval(cx-p-2, cy-p-2, cx+p+2, cy+p+2,
                                  fill="", outline="#6a0dad", width=1,
                                  stipple="gray25")
                    c.create_oval(cx-p, cy-p, cx+p, cy+p,
                                  fill=PIECE_BLACK_FILL,
                                  outline=PIECE_BLACK_OUTLINE, width=2)
                    c.create_oval(cx-p+5, cy-p+5, cx+p-5, cy+p-5,
                                  fill="", outline="#7b2fc0", width=1)
                elif v == WHITE:
                    wc += 1
                    # Moon
                    c.create_oval(cx-p, cy-p, cx+p, cy+p,
                                  fill=PIECE_WHITE_FILL,
                                  outline=PIECE_WHITE_OUTLINE, width=2)
                    c.create_oval(cx-p+4, cy-p+3, cx+p-10, cy+p-10,
                                  fill="#e8edf2", outline="")

        self._lbl_b.config(text=f"🕳 {self._d_black}: {bc}")
        self._lbl_w.config(text=f"🌙 {self._d_white}: {wc}")

        cur_name = self._d_black if self._cur == BLACK else self._d_white
        cur_col  = SUCC if self._cur == BLACK else DANG
        if self._running:
            self._lbl_turn.config(text=f"Turn {self._turn}  |  {cur_name}'s move",
                                   fg=cur_col)

    # ── Live piece-dominance chart ─────────────────────────────────────────────
    def _rebuild_chart(self):
        for w in self._chart_frame.winfo_children():
            w.destroy()
        if self._fig_cw:
            try: self._fig_cw.get_tk_widget().destroy()
            except: pass
            self._fig_cw = None

    def _update_chart(self):
        if not MPL or len(self._piece_track) < 2:
            return
        # Rebuild chart every 4 moves to avoid flicker
        if self._turn % 4 != 0:
            return

        for w in self._chart_frame.winfo_children():
            w.destroy()
        if self._fig_cw:
            try: self._fig_cw.get_tk_widget().destroy()
            except: pass

        fig = Figure(figsize=(4.2, 3.2), facecolor=CARD)
        ax  = fig.add_subplot(111)
        ax.set_facecolor(SURF)

        xs = [t for t, b, w in self._piece_track]
        yb = [b for t, b, w in self._piece_track]
        yw = [w for t, b, w in self._piece_track]

        ax.plot(xs, yb, color=SUCC, linewidth=1.5, label=f"⬛ {self._d_black}")
        ax.plot(xs, yw, color=DANG, linewidth=1.5, label=f"⬜ {self._d_white}")
        ax.fill_between(xs, yb, yw,
                        where=[b > w for b, w in zip(yb, yw)],
                        alpha=0.12, color=SUCC)
        ax.fill_between(xs, yb, yw,
                        where=[b <= w for b, w in zip(yb, yw)],
                        alpha=0.12, color=DANG)
        ax.axhline(32, color=BDR, linewidth=0.7, linestyle="--", alpha=0.5)
        ax.set_title("Piece Count Over Time",
                     color=TXT, fontsize=8, fontfamily="Georgia")
        ax.legend(fontsize=7, facecolor=CARD, edgecolor=BDR, labelcolor=TXT)
        for sp in ax.spines.values(): sp.set_color(BDR)
        ax.tick_params(colors=TXT2, labelsize=6)
        ax.set_ylabel("Pieces", color=TXT2, fontsize=7)
        ax.set_xlabel("Turn",   color=TXT2, fontsize=7)
        fig.tight_layout(pad=1.5)

        cw = FigureCanvasTkAgg(fig, master=self._chart_frame)
        cw.draw()
        cw.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._fig_cw = cw


# ═══════════════════════════════════════════════════════════════════════════════
# IDLE PREVIEW WINDOW  ─  screensaver-style AI vs AI over the start screen
# ═══════════════════════════════════════════════════════════════════════════════
class IdlePreviewWindow(tk.Toplevel):
    """
    Frameless overlay that plays a mini AI vs AI game.
    Appears after idle timeout on the start screen.
    Destroyed as soon as the user moves the mouse / presses a key.
    """

    SPEED = 480   # ms between moves

    def __init__(self, app: "App"):
        super().__init__(app)
        self.app      = app
        self._running = True
        self._job     = None
        self._board   = []
        self._cur     = BLACK
        self._turn    = 0
        self._track   = []

        # ── Window chrome ─────────────────────────────────────────────────────
        self.overrideredirect(True)      # no title bar
        self.attributes("-alpha", 0.0)  # start transparent for fade-in
        self.configure(bg=BG)
        self._position_over_parent()
        self.lift()

        self._build()
        self._reset()
        self._draw()
        self._fade_in()
        self._job = self.after(self.SPEED, self._step)

    def _position_over_parent(self):
        """Centre over the app window."""
        app = self.app
        aw, ah = app.winfo_width(), app.winfo_height()
        ax, ay = app.winfo_rootx(), app.winfo_rooty()
        W, H   = min(700, aw - 80), min(580, ah - 80)
        x = ax + (aw - W) // 2
        y = ay + (ah - H) // 2
        self.geometry(f"{W}x{H}+{x}+{y}")

    def _build(self):
        W = self.winfo_reqwidth() or 700

        # Accent border frame
        bdr = tk.Frame(self, bg=ACC, padx=2, pady=2)
        bdr.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(bdr, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True)

        # Header
        hdr = tk.Frame(inner, bg=SURF, pady=8)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="🤖  AI PREVIEW  —  CLICK ANYWHERE TO DISMISS",
                 font=("Georgia", 10, "bold"), bg=SURF, fg=TXT2).pack()

        # Body – board left, info right
        body = tk.Frame(inner, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Board (scaled down for the overlay)
        self._cell = 42
        cs = self._cell * BOARD_SIZE
        self._canvas = tk.Canvas(body, width=cs, height=cs,
                                  bg=BOARD_BG, highlightthickness=1,
                                  highlightbackground=BDR)
        self._canvas.pack(side=tk.LEFT)

        # Right info
        info = tk.Frame(body, bg=BG, padx=14)
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(info, text="WATCHING", font=("Georgia", 8, "bold"),
                 bg=BG, fg=TXT2).pack(anchor="w")

        # Matchup display
        diff_pairs = ["Easy vs Hard", "Medium vs Hard", "Hard vs Hard",
                      "Easy vs Medium", "Medium vs Medium"]
        self._matchup = random.choice(diff_pairs)
        parts = self._matchup.split(" vs ")
        self._diff_b = parts[0]
        self._diff_w = parts[1]

        tk.Label(info, text=f"⬛  {self._diff_b}",
                 font=F_BODY, bg=BG, fg=SUCC).pack(anchor="w", pady=(6,0))
        tk.Label(info, text="  vs", font=F_SMALL, bg=BG, fg=TXT2).pack(anchor="w")
        tk.Label(info, text=f"⬜  {self._diff_w}",
                 font=F_BODY, bg=BG, fg=DANG).pack(anchor="w")

        sep_f = tk.Frame(info, bg=BDR, height=1)
        sep_f.pack(fill=tk.X, pady=10)

        self._lbl_bc   = tk.Label(info, text="⬛ 2", font=F_MONO, bg=BG, fg=SUCC)
        self._lbl_bc.pack(anchor="w")
        self._lbl_wc   = tk.Label(info, text="⬜ 2", font=F_MONO, bg=BG, fg=DANG)
        self._lbl_wc.pack(anchor="w")
        self._lbl_turn = tk.Label(info, text="Turn 0", font=F_SMALL, bg=BG, fg=TXT2)
        self._lbl_turn.pack(anchor="w", pady=(6,0))

        sep_f2 = tk.Frame(info, bg=BDR, height=1)
        sep_f2.pack(fill=tk.X, pady=8)
        tk.Label(info, text="Move mouse or press any\nkey to start playing",
                 font=F_SMALL, bg=BG, fg=TXT2, justify=tk.LEFT).pack(anchor="w")

        # Click anywhere to dismiss
        for widget in [self, bdr, inner, hdr, body, self._canvas, info]:
            widget.bind("<ButtonPress>", lambda e: self.app._reset_idle())
            widget.bind("<Motion>",      lambda e: None)  # motion handled globally

    def _fade_in(self, alpha=0.0):
        if not self._running: return
        alpha = min(0.93, alpha + 0.06)
        try:
            self.attributes("-alpha", alpha)
        except Exception:
            return
        if alpha < 0.93:
            self.after(22, self._fade_in, alpha)

    # ── Game logic ────────────────────────────────────────────────────────────
    def _reset(self):
        self._board = [[EMPTY]*BOARD_SIZE for _ in range(BOARD_SIZE)]
        self._board[3][3] = self._board[4][4] = WHITE
        self._board[3][4] = self._board[4][3] = BLACK
        self._cur   = BLACK
        self._turn  = 0

    def _step(self):
        if not self._running: return
        moves = valid_moves(self._board, self._cur)
        if not moves:
            opp = WHITE if self._cur == BLACK else BLACK
            if not valid_moves(self._board, opp):
                # Game done — restart after short pause
                self._job = self.after(2000, self._restart)
                return
            self._cur = opp
            self._job = self.after(self.SPEED, self._step)
            return

        # Pick move based on difficulty
        diff = self._diff_b if self._cur == BLACK else self._diff_w
        is_max = (self._cur == WHITE)
        if diff == "Hard":
            model = self.app.ml_hard if self.app.ml_hard.ok else None
            _, mv = minimax(self._board, 2, float("-inf"), float("inf"), is_max, model)
            best  = mv if mv else random.choice(moves)
        elif diff == "Medium":
            model = self.app.ml_med if self.app.ml_med.ok else None
            _, mv = minimax(self._board, 1, float("-inf"), float("inf"), is_max, model)
            best  = mv if mv else random.choice(moves)
        else:
            best  = random.choice(moves)

        apply_move(self._board, self._cur, best[0], best[1])
        self._turn += 1
        self._cur = WHITE if self._cur == BLACK else BLACK
        self._draw()
        self._job = self.after(self.SPEED, self._step)

    def _restart(self):
        if not self._running: return
        # Pick a fresh random matchup
        pairs = ["Easy vs Hard", "Medium vs Hard", "Hard vs Hard",
                 "Easy vs Medium", "Medium vs Medium", "Easy vs Easy"]
        self._matchup = random.choice(pairs)
        parts = self._matchup.split(" vs ")
        self._diff_b, self._diff_w = parts[0], parts[1]
        self._reset()
        self._draw()
        self._job = self.after(self.SPEED, self._step)

    def _draw(self):
        c    = self._canvas
        cell = self._cell
        c.delete("all")

        for i in range(BOARD_SIZE + 1):
            c.create_line(i*cell, 0, i*cell, BOARD_SIZE*cell, fill=BOARD_LN, width=1)
            c.create_line(0, i*cell, BOARD_SIZE*cell, i*cell, fill=BOARD_LN, width=1)

        bc = wc = 0
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x0 = c * CELL_SIZE
                y0 = r * CELL_SIZE
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE
                cx = c*cell + cell//2
                cy = r*cell   + cell//2
                p  = cell//2 - 4
                v  = self._board[r][c]
                if v == BLACK:
                    bc += 1
                    c.create_oval(x0, y0, x1, y1,
                                  fill=PIECE_BLACK_FILL,
                                  outline=PIECE_BLACK_OUTLINE, width=1)
                elif v == WHITE:
                    wc += 1
                    c.create_oval(x0, y0, x1, y1,
                                  fill=PIECE_WHITE_FILL,
                                  outline=PIECE_WHITE_OUTLINE, width=1)

        try:
            self._lbl_bc.config(text=f"🕳  {bc}")
            self._lbl_wc.config(text=f"🌙  {wc}")
            self._lbl_turn.config(text=f"Turn {self._turn}")
        except Exception:
            pass

    # ── Teardown ──────────────────────────────────────────────────────────────
    def stop(self):
        self._running = False
        if self._job:
            try: self.after_cancel(self._job)
            except Exception: pass
            self._job = None
            
# ═══════════════════════════════════════════════════════════════════════════════
# Chaos Mode : Experimental and Chaotic
# ═══════════════════════════════════════════════════════════════════════════════
class ChaosManager:
    def __init__(self, gs):
        self.gs = gs
        self.board = gs.board
        self.turn_count = gs.turn_count
        self.pending_event = None
        self.pending_side = None
        self.pending_flippa_mode = None
        self.r = None
        self.c = None
        
        # Player-controlled events
        self.events = [
            ChaosEvent("No U", "Flips an entire row, column, or any non-corner 3x3 area", self.no_u_selector),
            ChaosEvent("Mirror", "Places the same colored piece on the opposide side", self.mirror),
            ChaosEvent("Propagation", "Converts random adjacent pieces to the same color", self.propagation),
            ChaosEvent("Amogus", "Forcibly converts all non-edge pieces to the same color, even if it shouldn't be possible", self.amogus),
            ChaosEvent("Divine Smite", "Changes a chosen 3x3 non-edge area to the same color", self.divine_smite)
        ]
        # Normal trigger probability = 100
        # Function : Prob(X = event)/SUM(Prob(events)
        # self.events_probs = [70, 50, 80, 10, 20]
        self.events_probs = [0, 10, 0, 0, 10]
        
        # Board events (helps the AI gain an advantage)
        self.environments = [
            ChaosEvent("Tidal Surge", "Flushes an entire row or column of pieces", self.tidal_surge),
            ChaosEvent("Void", "Removes some tiles permanently (reversible by Divine Smite)", self.void),
            ChaosEvent("Rainy Days", "Spawns random pieces on non-corner locations", self.rainy_days),
            ChaosEvent("Stargazer", "On 3 random rows or columns, change all black pieces to white", self.stargazer),
            ChaosEvent("Earthquake", "Shifts every piece vertically or horizontally by some magnitude", self.earthquake),
            ChaosEvent("Starfall", "Destroys all pieces within some number of random 2x2 areas", self.starfall),
            ChaosEvent("Rage Quit", "50% chance to destroy any piece for all pieces", self.rage_quit)
        ]
        
        # Normal trigger probability = 100
        # Function : Prob(X = event)/SUM(Prob(events)
        # self.environments_probs = [100, 40, 40, 50, 60, 20, 10]
        self.environments_probs = [100, 0, 0, 0, 60, 0, 0]
        
    def next_event(self):
        if self.turn_count % 4 == 0:  # trigger every 4 turns
            return self.trigger_event()
        return None, None
    
    def weighted_choices(self, events, probs, n):
        # Build cumulative thresholds
        cumulative = []
        running_total = 0
        for p in probs:
            running_total += p
            cumulative.append(running_total)

        total = cumulative[-1]
        results = []

        while len(results) < n:
            r = random.uniform(0, total)
            for event, threshold in zip(events, cumulative):
                if r <= threshold:
                    if event not in results:   # avoid duplicates
                        results.append(event)
                    break
        return results

    def trigger_event(self):
        side = random.choice([BLACK, WHITE])
        if (side == BLACK):
            events = self.weighted_choices(self.events, self.events_probs, 2)
        else : events = self.weighted_choices(self.environments, self.environments_probs, 1)
        return side, events

    def event_selector(self, side, events):
        if side == BLACK:
            # Use the root window as parent
            win = tk.Toplevel()
            win.title("Choose Your Chaos Modifier")
            for event in events:
                btn = mkbtn(
                    win,
                    event.name,
                    lambda e=event: self.apply_and_close(win, e, side)
                )
                btn.pack(padx=10, pady=5)
            tk.Label(win, text="Pick one chaos power to unleash!").pack()
        else:
            self.apply_event(events[0], side)

    def apply_event(self, event, side):
        # Environment events (AI side) fire immediately — they don't need a click.
        # Player events need the human to click a cell first; store them as pending.
        player_event_names = {"Mirror", "Propagation", "Amogus", "Divine Smite"}
        if side == BLACK and event.name in player_event_names:
            self.pending_event = event
            self.pending_side  = side
            self.pending_flippa_mode = None
            self.gs.canvas.bind("<Button-1>", self.chaos_click)
            return

        # No U opens its own selector popup and sets pending state itself.
        if side == BLACK and event.name == "No U":
            self.no_u_selector(self.board)
            return

        # AI / environment event — fire immediately
        player = side
        event.apply(
            self.board, self.r, self.c, player,
            self.gs.chaos_animator,
            done_cb=self._on_anim_done
        )
        self.log_event(event.name, side)

    def apply_and_close(self, popup, event, side):
        self.apply_event(event, side)
        popup.destroy()

    def log_event(self, msg, side):
        time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("Chaos Events Log.txt", "a") as f:
            f.write(f"{time} | Player:{side} | Turn:{int(self.turn_count)} | Event:{msg}\n")

    def chaos_click(self, e):
        r = int(e.y / CELL_SIZE)
        c = int(e.x / CELL_SIZE)
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
            return
        if self.pending_event:
            player = BLACK  # player events are always the human player
            self.pending_event.apply(
                self.board, r, c, player,
                self.gs.chaos_animator,
                done_cb=self._on_anim_done,
                **({'mode': self.pending_flippa_mode} if self.pending_flippa_mode else {})
            )
            self.log_event(self.pending_event.name, self.pending_side)
            self.pending_event      = None
            self.pending_side       = None
            self.pending_flippa_mode = None
            if self.r is None:
                self.r = r
                self.c = c
            else : 
                self.r = None
                self.c = None

    def _on_anim_done(self):
        self.gs._draw()
        self.gs.canvas.bind("<Button-1>", self.gs._click)
  
    # --- Handy Functions ---
    def non_edge_checker(self, r, c):
        edges = [0, BOARD_SIZE - 1]
        checker = True if (r not in edges) and (c not in edges) else False
        if checker : 
            return True
        else : 
            messagebox.showwarning("Invalid", "You cannot choose an edge cell. Try again.")
            return False

    # --- Events ---    
    def no_u(self, board, r, c, mode): # Flips any row, column, or non-edge 3x3 area
        if self.non_edge_checker(r, c):
            if mode == "row":
                for column in range(BOARD_SIZE):
                    if board[r][column] not in (EMPTY, None):  # skip empty and void
                        board[r][column] = WHITE if board[r][column] == BLACK else BLACK
                self.log_event(f"No U flipped row {r}", "Player")

            elif mode == "col":
                for row in range(BOARD_SIZE):
                    if board[row][c] not in (EMPTY, None):
                        board[row][c] = WHITE if board[row][c] == BLACK else BLACK
                self.log_event(f"No U flipped column {c}", "Player")

            elif mode == "block":
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if board[r+dr][c+dc] not in (EMPTY, None):
                            board[r+dr][c+dc] = WHITE if board[r+dr][c+dc] == BLACK else BLACK
                    self.log_event(f"No U flipped 3x3 block centered at ({r},{c})", "Player")
        return [mode, r, c]
    
    def no_u_selector(self, board, **kwargs):
        # Create popup window
        win = tk.Toplevel(self.gs)
        win.title("Choose No U Mode")

        # Instruction label
        tk.Label(win, text="Select how to flip:").pack(pady=5)

        # Button for row mode
        btn_row = mkbtn(
            win,
            "Flip Row",
            lambda: self.apply_flippa_and_close(win, board, "row")
        )
        btn_row.pack(padx=10, pady=5)

        # Button for column mode
        btn_col = mkbtn(
            win,
            "Flip Column",
            lambda: self.apply_flippa_and_close(win, board, "col")
        )
        btn_col.pack(padx=10, pady=5)

        # Button for block mode
        btn_block = mkbtn(
            win,
            "Flip 3x3 Block",
            lambda: self.apply_flippa_and_close(win, board, "block")
        )
        btn_block.pack(padx=10, pady=5)

    def apply_flippa_and_close(self, popup, board, mode):
        popup.destroy()
        self.pending_flippa_mode = mode
        self.gs.canvas.bind("<Button-1>", self.flippa_click)

    def flippa_click(self, e):
        r = int(e.y / CELL_SIZE)
        c = int(e.x / CELL_SIZE)
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
            return
        self.no_u(self.board, self.pending_flippa_mode, r, c)
        self.gs._draw()
        self.gs.canvas.bind("<Button-1>", self.gs._click)

    def mirror(self, board, r, c, **kwargs): # Place piece at mirrored coord; flip the straight line between the two points
        if ([r, c]) not in valid_moves(board, BLACK): 
            return None
        player = BLACK
        mr, mc = BOARD_SIZE - 1 - r, BOARD_SIZE - 1 - c  # mirrored position

        # Place piece at the clicked cell (normal rule-bound move)
        piece1 = apply_move(board, player, r, c)

        # Place piece at the mirrored cell (force-place, no normal flip rules)
        board[mr][mc] = player

        # Flip every piece along the straight line between (r,c) and (mr,mc).
        # Only works when they share a row, column, or diagonal (i.e. a true line).
        flipped_line = []
        dr = mr - r
        dc = mc - c
        steps = max(abs(dr), abs(dc))
        if steps > 0 and (dr == 0 or dc == 0 or abs(dr) == abs(dc)):
            step_r = dr // steps
            step_c = dc // steps
            nr, nc = r + step_r, c + step_c
            while (nr, nc) != (mr, mc):
                if board[nr][nc] not in (EMPTY, None):
                    board[nr][nc] = player
                    flipped_line.append([nr, nc])
                nr += step_r
                nc += step_c

        self.log_event(
            f"Mirror: placed at ({r},{c}), mirrored at ({mr},{mc}), "
            f"flipped {len(flipped_line)} pieces along the line", "Player"
        )
        return [r, c, mr, mc]

    def propagation(self, board, r, c, **kwargs): # Infection-based conversion 
        if not self.non_edge_checker(r, c):
            return

        burning_pieces = [(r, c)]
        spread = random.randint(7, 12)
        while (len(burning_pieces) < spread): 
            for i in range(spread):
                cluster = burning_pieces[:]
                for pos in cluster: #br = burning row, bc = burning column
                    br, bc = pos[0], pos[1]
                    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    candidates = []
                    for dr, dc in directions:
                        cr, cc  = br+dr, bc+dc #cr, candidate row, cc = candidate column
                        if (0 <= cr <= BOARD_SIZE -1) and (0 <= cc <= BOARD_SIZE - 1): # No going out-of-bounds
                            if (board[cr][cc] not in (EMPTY, None)) and (board[cr][cc] != BLACK):
                                candidates.append([cr, cc])
                if candidates: #Randomly picking any adjacent cell
                    choice = random.choice(candidates)
                    nbr, nbc = choice # nbr = new burning row, nbc = new burning column
                    board[nbr][nbc] = BLACK
                    burning_pieces.append([nbr, nbc])
                else : return # If no candidates, no use iterating more
        self.log_event(f"Fire spreads to {burning_pieces}", "Player") 
        return burning_pieces

    def amogus(self, board, r, c, **kwargs): # Force-converts all enemy pieces in 8 directions
        board[r][c] = BLACK
        hits = []
        
        # Setting up the 8 directions
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dr, dc in directions:
            hr, hc = r + dr, c + dc # hr = hit row, hc = hit column
            while (0 <= hr < BOARD_SIZE) and (0 <= hc < BOARD_SIZE):
                if (board[hr][hc] in (EMPTY, None)): break
                if (board[hr][hc] != BLACK):
                    board[hr][hc] = BLACK
                    dist = max(abs(hr - r), abs( hc - c))
                    hits.append(([hr, hc], dist))
                hr += dr
                hc += dc
                
        # Sort by distance for animating        
        hits.sort(key = lambda x : x[1])
        self.log_event(f"Amogus played at ({r}, {c}) and converted {hits} pieces", "Player")
        return hits
                
    def divine_smite(self, board, r, c, player=BLACK):
        if not self.non_edge_checker(r, c): return
        hits = []        
        hits.append([r, c])
        board[r][c] = player
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if (board[nr][nc] == None) :
                board[nr][nc] = EMPTY
            else : board[nr][nc] = player
            hits.append([nr, nc])
        self.log_event(f"Cell ({r}, {c}) was smited by divine beings", "Player")
        return hits

    # --- Board Environments --- 
    def tidal_surge(self, board):
        axis = random.choice(["row", "column"])
        index = random.randint(0, BOARD_SIZE - 1)
        if (axis == "row") : 
            for cell in range(BOARD_SIZE) :
                if board[index][cell] not in (EMPTY, None):
                    board[index][cell] =  EMPTY
        else:
            for cell in range(BOARD_SIZE):
                if board[cell][index] not in (EMPTY, None):
                    board[cell][index] = EMPTY
        self.log_event(f"Tidal Surge flushed {axis} {index}", "AI")
        return [axis, index]
    
    def void(self, board):
        hits = []
        num_voids = random.randint(5, 10)  # how many tiles to delete
        while (len(hits) < num_voids):
            r, c = random.randint(0, BOARD_SIZE - 1), random.randint(0, BOARD_SIZE - 1)
            if (board[r][c] is not None):
                hits.append([r, c]) 
                board[r][c] = None  # mark as void (cannot be interacted with)
        self.log_event(f"Void removed {num_voids} tiles", "AI")
        return hits
        
    def rainy_days(self, board):
        hits = []
        attempts = 0
        target = random.randint(8, 12)
        while True:
            if (attempts == target) : break
            r = random.randint(0, BOARD_SIZE - 1)
            c = random.randint(0, BOARD_SIZE - 1)
            if (r, c) in [(0, 0), (0, BOARD_SIZE - 1), (BOARD_SIZE - 1, 0), (BOARD_SIZE - 1, BOARD_SIZE - 1)]: continue
            if (board[r][c] is not None) and ([r, c] not in hits) :
                board[r][c] = random.choice([BLACK, WHITE])
                hits.append([r, c])
                attempts += 1
            else : continue
        self.log_event(f"Rainy Days spawned {len(hits)} pieces", "AI")
        return hits

    def stargazer(self, board):
        hits = []
        flipped = 0
        while True:
            if (len(hits) >=  3) : break 
            mode = random.choice(["row", "column"])
            index = random.randint(0, BOARD_SIZE - 1)
            if ([mode, index] in hits) :
                continue
            else : 
                if (mode == "row") :
                    for i in range(BOARD_SIZE):
                        if (board[index][i] == BLACK):
                            board[index][i] = WHITE
                            flipped += 1
                else : 
                    for i in range(BOARD_SIZE):
                        if (board[i][index] == BLACK):
                            board[i][index] = WHITE
                            flipped += 1
            hits.append([mode, index])
        self.log_event(f"Stargazer triggered and flipped {flipped} pieces", "AI")
        return hits

    def earthquake(self, board):
        mag_scale = [1, 2, 3]
        mag_probs = [50, 35, 15]
        magnitude = self.weighted_choices(mag_scale, mag_probs, 1)
        direction = ["left", "right", "up", "down"]
        for i in range(magnitude[0]):
            choice = random.choice(direction)
            match choice:
                case "left":
                    for r in range(BOARD_SIZE):
                        for c in range(BOARD_SIZE - 1):
                            board[r][c] = board[r][c + 1]
                        board[r][BOARD_SIZE -1] = EMPTY
                
                case "right":
                    for r in range(BOARD_SIZE):
                        for c in range(BOARD_SIZE - 1, 0, -1):
                            board[r][c] = board[r][c - 1]
                        board[r][0] = EMPTY
                
                case "up": 
                    for c in range(BOARD_SIZE):
                        for r in range(BOARD_SIZE - 1):
                            board[r][c] = board[r + 1][c]
                        board[BOARD_SIZE - 1][c] = EMPTY
                
                case "down":
                    for c in range(BOARD_SIZE):
                        for r in range(BOARD_SIZE - 1, 0, -1):
                            board[r][c] = board[r - 1][c]
                        board[0][c] = EMPTY
        self.log_event(f"Earthquake shifts every piece to the {choice}", "AI")
        return choice

    def starfall(self, board):
        hits = []
        target = random.randint(4, 8)
        while (len(hits) < target):
            r = random.randint(0, BOARD_SIZE - 2)
            c = random.randint(0, BOARD_SIZE - 2)
            if ([r, c] in hits) : continue 

            for dr in range(2):
                for dc in range(2):
                    board[r + dr][c + dc] = EMPTY
            hits.append([r, c])
        self.log_event(f"Starfall destroyed {target} 2x2 areas", "AI")
        return hits

    def rage_quit(self, board):
        hits = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] not in (EMPTY, None):
                    if random.choice([True, False]):  # 50/50
                        board[r][c] = EMPTY
                        hits.append([r, c])
        self.log_event(f"Rage Quit triggered, {len(hits)} pieces destroyed", "AI")
        return hits

class ChaosAnimator:
    """
    Drives every chaos visual effect.
    Holds a reference to the GameScreen (`gs`) for canvas access and
    `after()` scheduling.  All drawing uses tag "chaos_anim".
    """

    TAG = "chaos_anim"

    # ── Colour palette (matches the Scholar's Study theme) ────────────────────
    _FIRE_COLS   = ["#FF6600", "#FF4400", "#FF2200", "#FF8800", "#FFAA00"]
    _MIST_COL    = "#A8D8FF"
    _BEAM_COL    = "#FFFAAA"
    _SMITE_COL   = "#FFE066"
    _RIVER_COLS  = ["#1A6FBF", "#2288DD", "#44AAFF", "#66CCFF", "#88DDFF"]
    _VOID_STEPS  = 12          # darkening steps for void
    _GLOW_COL    = "#FFFFAA"   # stargazer / starfall glow
    _RAGE_COL    = "#CC0000"   # rage-quit red
    _QUAKE_DIST  = 10          # pixels board shakes per step
    _RAIN_COL    = "#5599FF"   # raindrop shadow

    def __init__(self, gs):
        self.gs = gs

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _cx(self, c):
        return int(c * CELL_SIZE + CELL_SIZE * 0.5)

    def _cy(self, r):
        return int(r * CELL_SIZE + CELL_SIZE * 0.5)

    def _r(self):
        """Piece radius on the current board."""
        return CELL_SIZE // 2 - 5

    def _clear(self):
        self.gs.canvas.delete(self.TAG)

    def _finish(self, done_cb):
        self._clear()
        self.gs._draw()
        done_cb()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. No U — every affected piece does a horizontal squeeze-flip
    #    result = [mode, r, c]   (mode = "row" | "col" | "block")
    # ─────────────────────────────────────────────────────────────────────────

    def animate_no_u(self, result, player, done_cb):
        mode, r, c = result

        # Collect the (r, c) pairs that were actually flipped
        cells = []
        if mode == "row":
            cells = [(r, col) for col in range(BOARD_SIZE)]
        elif mode == "col":
            cells = [(row, c) for row in range(BOARD_SIZE)]
        elif mode == "block":
            cells = [(r + dr, c + dc)
                     for dr in range(-1, 2) for dc in range(-1, 2)]

        # Filter to non-empty, non-void cells
        board = self.gs.board
        cells = [(rr, cc) for rr, cc in cells
                 if board[rr][cc] not in (EMPTY, None)]

        frames   = 8          # steps to squeeze to zero width
        p        = self._r()
        fill_col = PIECE_BLACK_FILL if player == BLACK else PIECE_WHITE_FILL
        opp_col  = PIECE_WHITE_FILL if player == BLACK else PIECE_BLACK_FILL

        def step(i):
            self._clear()
            ratio = 1.0 - i / frames if i <= frames else (i - frames) / frames
            color = fill_col if i > frames else opp_col
            for rr, cc in cells:
                cx = self._cx(cc)
                cy = self._cy(rr)
                rx = max(1, int(p * ratio))
                self.gs.canvas.create_oval(
                    cx - rx, cy - p, cx + rx, cy + p,
                    fill=color, outline="", tags=self.TAG)
            if i < frames * 2:
                self.gs.after(28, step, i + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        step(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. MIRROR — beam of light between both pieces, then flip ripple outward
    #    result = [r, c, mr, mc]
    # ─────────────────────────────────────────────────────────────────────────

    def animate_mirror(self, result, player, done_cb):
        if not result: 
            done_cb(); return
        r, c, mr, mc = result
        cx1, cy1 = self._cx(c),  self._cy(r)
        cx2, cy2 = self._cx(mc), self._cy(mr)
        p = self._r()
        beam_frames = 12
        glow_frames = 8

        def beam_step(i):
            self._clear()
            # Draw pulsing beam between the two pieces
            alpha_ratio = i / beam_frames
            width = max(1, int(6 * (1 - alpha_ratio)))
            self.gs.canvas.create_line(
                cx1, cy1, cx2, cy2,
                fill=self._BEAM_COL, width=width,
                tags=self.TAG)
            # Glow rings on both endpoints
            for cx, cy in [(cx1, cy1), (cx2, cy2)]:
                halo = int(p * (1 + 0.5 * alpha_ratio))
                self.gs.canvas.create_oval(
                    cx - halo, cy - halo, cx + halo, cy + halo,
                    outline=self._BEAM_COL, width=2, fill="", tags=self.TAG)
            if i < beam_frames:
                self.gs.after(30, beam_step, i + 1)
            else:
                glow_step(0)

        def glow_step(i):
            self._clear()
            self.gs._draw()
            # Expanding ring from each piece
            for cx, cy in [(cx1, cy1), (cx2, cy2)]:
                radius = p + int(p * 1.5 * i / glow_frames)
                alpha  = 1.0 - i / glow_frames
                width  = max(1, int(4 * alpha))
                self.gs.canvas.create_oval(
                    cx - radius, cy - radius,
                    cx + radius, cy + radius,
                    outline=self._BEAM_COL, width=width,
                    fill="", tags=self.TAG)
            if i < glow_frames:
                self.gs.after(30, glow_step, i + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        beam_step(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Propagation — pieces catch fire one-by-one sorted by distance
    #    result = [[r,c], [r,c], ...]   (burning_pieces list)
    # ─────────────────────────────────────────────────────────────────────────

    def animate_propagation(self, result, player, done_cb):
        if not result:
            done_cb(); return

        fire_frames = 10
        p = self._r()

        def burn_piece(idx):
            if idx >= len(result):
                self._finish(done_cb)
                return
            rr, cc = result[idx]
            cx = self._cx(cc)
            cy = self._cy(rr)
            _animate_flame(idx, cx, cy, 0)

        def _animate_flame(idx, cx, cy, frame):
            if frame <= fire_frames:
                # Draw flickering flame tongues
                self.gs.canvas.delete(f"fire_{idx}")
                num_tongues = 5
                for t in range(num_tongues):
                    offset_x = random.randint(-p // 2, p // 2)
                    height   = random.randint(p // 2, p + 4)
                    col      = random.choice(self._FIRE_COLS)
                    self.gs.canvas.create_oval(
                        cx + offset_x - 5, cy - height,
                        cx + offset_x + 5, cy + p // 3,
                        fill=col, outline="",
                        tags=(self.TAG, f"fire_{idx}"))
                self.gs.after(40, _animate_flame, idx, cx, cy, frame + 1)
            else:
                self.gs.canvas.delete(f"fire_{idx}")
                # Short pause then ignite next piece
                self.gs.after(60, burn_piece, idx + 1)

        self.gs._draw()
        burn_piece(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Amogus — mist shoots out in 8 directions from the center
    #    result = [([r,c], dist), ...]  sorted by distance
    # ─────────────────────────────────────────────────────────────────────────

    def animate_amogus(self, result, player, done_cb):
        if not result:
            done_cb(); return

        # Group by distance wave
        waves = {}
        for (pos, dist) in result:
            waves.setdefault(dist, []).append(pos)
        sorted_dists = sorted(waves.keys())

        p         = self._r()
        mist_col  = self._MIST_COL
        wave_delay = 80   # ms between distance waves

        def show_wave(wave_idx):
            if wave_idx >= len(sorted_dists):
                self._finish(done_cb)
                return
            d    = sorted_dists[wave_idx]
            cell_list = waves[d]
            _mist_puff(cell_list, 0, wave_idx)

        def _mist_puff(cell_list, frame, wave_idx):
            puff_frames = 6
            for pos in cell_list:
                rr, cc = pos
                cx = self._cx(cc)
                cy = self._cy(rr)
                self.gs.canvas.delete(f"mist_{wave_idx}")
                radius = p // 2 + int(p * 0.8 * frame / puff_frames)
                alpha_w = max(1, int(3 * (1 - frame / puff_frames)))
                self.gs.canvas.create_oval(
                    cx - radius, cy - radius,
                    cx + radius, cy + radius,
                    outline=mist_col, width=alpha_w,
                    fill="", tags=(self.TAG, f"mist_{wave_idx}"))
            if frame < puff_frames:
                self.gs.after(35, _mist_puff, cell_list, frame + 1, wave_idx)
            else:
                self.gs.canvas.delete(f"mist_{wave_idx}")
                self.gs.after(wave_delay, show_wave, wave_idx + 1)

        self.gs._draw()
        show_wave(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. DIVINE SMITE — affected pieces light up with a golden flash
    #    result = [[r,c], ...]
    # ─────────────────────────────────────────────────────────────────────────

    def animate_divine_smite(self, result, player, done_cb):
        if not result:
            done_cb(); return

        p           = self._r()
        smite_col   = self._SMITE_COL
        flash_frames = 10

        def flash(frame):
            self._clear()
            ratio  = 1.0 - frame / flash_frames
            radius = p + int(p * 0.6 * ratio)
            width  = max(1, int(5 * ratio))
            for pos in result:
                rr, cc = pos
                cx = self._cx(cc)
                cy = self._cy(rr)
                # Outer glow ring
                self.gs.canvas.create_oval(
                    cx - radius, cy - radius,
                    cx + radius, cy + radius,
                    outline=smite_col, width=width,
                    fill="", tags=self.TAG)
                # Inner gold fill fading out
                if ratio > 0.3:
                    self.gs.canvas.create_oval(
                        cx - p, cy - p, cx + p, cy + p,
                        fill=smite_col, outline="", tags=self.TAG)
            if frame < flash_frames:
                self.gs.after(30, flash, frame + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        flash(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. TIDAL SURGE — a river flows across the cleared row or column
    #    result = [axis, index]   axis = "row" | "column"
    # ─────────────────────────────────────────────────────────────────────────

    def animate_tidal_surge(self, result, player, done_cb):
        axis, index = result
        board_px    = CELL_SIZE * BOARD_SIZE
        wave_count  = 5
        wave_frames = 20

        def draw_wave(frame):
            self._clear()
            progress = frame / wave_frames  # 0 → 1 across the board

            for w in range(wave_count):
                offset = (progress + w / wave_count) % 1.0
                col    = self._RIVER_COLS[w % len(self._RIVER_COLS)]
                width  = max(2, int(CELL_SIZE * 0.25))

                if axis == "row":
                    x = int(offset * board_px)
                    y0 = index * CELL_SIZE
                    y1 = y0 + CELL_SIZE
                    self.gs.canvas.create_line(
                        x, y0, x, y1,
                        fill=col, width=width, tags=self.TAG)
                else:
                    y = int(offset * board_px)
                    x0 = index * CELL_SIZE
                    x1 = x0 + CELL_SIZE
                    self.gs.canvas.create_line(
                        x0, y, x1, y,
                        fill=col, width=width, tags=self.TAG)

            if frame < wave_frames:
                self.gs.after(30, draw_wave, frame + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        draw_wave(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. VOID — tiles gradually darken to pure black then vanish
    #    result = [[r,c], ...]
    # ─────────────────────────────────────────────────────────────────────────

    def animate_void(self, result, player, done_cb):
        if not result:
            done_cb(); return

        p      = self._r()
        steps  = self._VOID_STEPS

        def darken(step):
            self._clear()
            ratio = step / steps   # 0 → 1
            # Interpolate from board-bg colour toward pure black
            r_val = int(0x4A * (1 - ratio))
            g_val = int(0x2E * (1 - ratio))
            b_val = int(0x14 * (1 - ratio))
            col   = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            for pos in result:
                rr, cc = pos
                x0 = cc * CELL_SIZE
                y0 = rr * CELL_SIZE
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE
                self.gs.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=col, outline="", tags=self.TAG)
            if step < steps:
                self.gs.after(40, darken, step + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        darken(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. RAINY DAYS — a shadow falls from above before the piece lands
    #    result = [[r,c], ...]
    # ─────────────────────────────────────────────────────────────────────────

    def animate_rainy_days(self, result, player, done_cb):
        if not result:
            done_cb(); return

        p         = self._r()
        drop_steps = 12

        # Drop all pieces simultaneously
        def drop(step):
            self._clear()
            progress = step / drop_steps   # 0 → 1  (top of cell → centre)
            for pos in result:
                rr, cc = pos
                cx = self._cx(cc)
                # Shadow grows on the cell as drop approaches
                shadow_alpha = progress
                shadow_r     = int(p * shadow_alpha)
                if shadow_r > 1:
                    self.gs.canvas.create_oval(
                        cx - shadow_r, self._cy(rr) - shadow_r // 2,
                        cx + shadow_r, self._cy(rr) + shadow_r // 2,
                        fill=self._RAIN_COL, outline="",
                        stipple="gray25", tags=self.TAG)
                # Raindrop falling from top of cell
                drop_y = int(rr * CELL_SIZE + CELL_SIZE * progress)
                self.gs.canvas.create_oval(
                    cx - 4, drop_y - 8,
                    cx + 4, drop_y + 4,
                    fill=self._RAIN_COL, outline="", tags=self.TAG)

            if step < drop_steps:
                self.gs.after(30, drop, step + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        drop(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 9. STARGAZER — affected rows/columns glow bright before pieces change
    #    result = [[mode, index], ...]   mode = "row" | "column"
    # ─────────────────────────────────────────────────────────────────────────

    def animate_stargazer(self, result, player, done_cb):
        if not result:
            done_cb(); return

        board_px    = CELL_SIZE * BOARD_SIZE
        glow_frames = 14
        glow_col    = self._GLOW_COL

        def glow(frame):
            self._clear()
            # Peak brightness at mid-point, fade out after
            ratio = (1.0 - abs(frame / glow_frames - 0.5) * 2)
            width = max(1, int(CELL_SIZE * ratio))
            for entry in result:
                mode, index = entry
                if mode == "row":
                    y = index * CELL_SIZE + CELL_SIZE // 2
                    self.gs.canvas.create_line(
                        0, y, board_px, y,
                        fill=glow_col, width=width, tags=self.TAG)
                else:
                    x = index * CELL_SIZE + CELL_SIZE // 2
                    self.gs.canvas.create_line(
                        x, 0, x, board_px,
                        fill=glow_col, width=width, tags=self.TAG)
            if frame < glow_frames:
                self.gs.after(30, glow, frame + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        glow(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 10. EARTHQUAKE — the whole board shudders side-to-side
    #     result = choice   ("left" | "right" | "up" | "down")
    # ─────────────────────────────────────────────────────────────────────────

    def animate_earthquake(self, result, player, done_cb):
        direction = result
        shakes    = 8        # total oscillation half-cycles
        dist      = self._QUAKE_DIST
        delay     = 35

        # Determine shake axis
        dx = dist if direction in ("left", "right") else 0
        dy = dist if direction in ("up",   "down")  else 0

        def shake(step):
            self._clear()
            sign = 1 if step % 2 == 0 else -1
            fade = 1.0 - step / shakes
            ox   = int(dx * sign * fade)
            oy   = int(dy * sign * fade)

            # Shift every canvas item tagged "el" temporarily
            self.gs.canvas.move("el", ox, oy)
            # Schedule move-back + next step
            def restore_and_continue():
                self.gs.canvas.move("el", -ox, -oy)
                if step < shakes:
                    self.gs.after(delay, shake, step + 1)
                else:
                    self._finish(done_cb)
            self.gs.after(delay, restore_and_continue)

        self.gs._draw()
        shake(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 11. STARFALL — each 2×2 area glows before being cleared (like Stargazer)
    #     result = [[r,c], ...]   top-left corners of the 2×2 areas
    # ─────────────────────────────────────────────────────────────────────────

    def animate_starfall(self, result, player, done_cb):
        if not result:
            done_cb(); return

        glow_frames = 12
        glow_col    = self._GLOW_COL

        def glow(frame):
            self._clear()
            ratio = 1.0 - abs(frame / glow_frames - 0.5) * 2
            for pos in result:
                rr, cc = pos
                x0 = cc * CELL_SIZE
                y0 = rr * CELL_SIZE
                x1 = x0 + CELL_SIZE * 2
                y1 = y0 + CELL_SIZE * 2
                # Expanding bright rectangle
                inset = int(CELL_SIZE * (1 - ratio) * 0.4)
                self.gs.canvas.create_rectangle(
                    x0 + inset, y0 + inset,
                    x1 - inset, y1 - inset,
                    fill=glow_col, outline="",
                    stipple="gray50", tags=self.TAG)
                self.gs.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    outline=glow_col, width=max(1, int(4 * ratio)),
                    fill="", tags=self.TAG)
            if frame < glow_frames:
                self.gs.after(30, glow, frame + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        glow(0)

    # ─────────────────────────────────────────────────────────────────────────
    # 12. RAGE QUIT — pieces turn red then "explode" (scatter + shrink)
    #     result = [[r,c], ...]
    # ─────────────────────────────────────────────────────────────────────────

    def animate_rage_quit(self, result, player, done_cb):
        if not result:
            done_cb(); return

        p          = self._r()
        red_frames = 8
        exp_frames = 10
        rage_col   = self._RAGE_COL

        # Phase 1: turn red
        def redden(frame):
            self._clear()
            ratio = frame / red_frames
            for pos in result:
                rr, cc = pos
                cx = self._cx(cc)
                cy = self._cy(rr)
                # Blend piece fill toward rage_col via overlay oval
                self.gs.canvas.create_oval(
                    cx - p, cy - p, cx + p, cy + p,
                    fill=rage_col, outline="",
                    stipple="gray50" if ratio < 0.6 else "",
                    tags=self.TAG)
            if frame < red_frames:
                self.gs.after(35, redden, frame + 1)
            else:
                explode(0)

        # Phase 2: scatter + shrink
        _offsets = {
            tuple(pos): (
                random.randint(-CELL_SIZE, CELL_SIZE),
                random.randint(-CELL_SIZE, CELL_SIZE)
            )
            for pos in result
        }

        def explode(frame):
            self._clear()
            ratio = frame / exp_frames
            for pos in result:
                rr, cc = pos
                cx = self._cx(cc)
                cy = self._cy(rr)
                ox, oy = _offsets[tuple(pos)]
                ex = cx + int(ox * ratio)
                ey = cy + int(oy * ratio)
                pr = max(1, int(p * (1 - ratio)))
                self.gs.canvas.create_oval(
                    ex - pr, ey - pr, ex + pr, ey + pr,
                    fill=rage_col, outline="", tags=self.TAG)
            if frame < exp_frames:
                self.gs.after(28, explode, frame + 1)
            else:
                self._finish(done_cb)

        self.gs._draw()
        redden(0)


# ═══════════════════════════════════════════════════════════════════════════════
# ChaosEvent  —  replaces the old stub
# ═══════════════════════════════════════════════════════════════════════════════

class ChaosEvent:
    """
    Represents one chaos power.

    Attributes
    ──────────
    name        : str   — display name shown in the popup
    description : str   — flavour text shown in the popup
    func        : callable(board, ...)  — the ChaosManager method that mutates
                  the board and returns animation data
    anim_key    : str   — matches a ChaosAnimator.animate_<anim_key> method

    Usage
    ─────
    After the board has been mutated by calling event.func(...), trigger the
    matching animation with:

        animator.animate_<anim_key>(result, player, done_cb)

    The GameScreen's ChaosManager wires this up in chaos_click / apply_event.
    """

    # Maps each event name to its animator method name
    _ANIM_MAP = {
        "No U":      "no_u",
        "Mirror":             "mirror",
        "Propagation":        "propagation",
        "Amogus": "amogus",
        "Divine Smite":       "divine_smite",
        "Tidal Surge":        "tidal_surge",
        "Void":               "void",
        "Rainy Days":         "rainy_days",
        "Stargazer":          "stargazer",
        "Earthquake":         "earthquake",
        "Starfall":           "starfall",
        "Rage Quit":          "rage_quit",
    }

    def __init__(self, name: str, description: str, func):
        self.name        = name
        self.description = description
        self.func        = func               # the ChaosManager method
        self.anim_key    = self._ANIM_MAP.get(name, None)

    # ── apply() mutates the board and fires the animation ─────────────────────
    def apply(self, board, r, c, player, animator: "ChaosAnimator", done_cb,
              **kwargs):
        """
        1. Calls self.func to mutate the board and collect the result.
        2. Immediately starts the matching animation.
        3. Calls done_cb() when the animation finishes.

        Parameters
        ──────────
        board     : the live game board (2-D list)
        r, c      : clicked cell coordinates (used by player events;
                    ignored by environment events that take no coordinates)
        player    : BLACK or WHITE
        animator  : the ChaosAnimator instance attached to the GameScreen
        done_cb   : called with no arguments once the animation completes
        **kwargs  : extra params forwarded to self.func (e.g. mode= for
                    No U, player= for Divine Smite)
        """
        # ── Call the board-mutation function ──────────────────────────────────
        # Determine how to call func based on what it needs.
        # Environment events (Tidal Surge, Void, etc.) take only board.
        # Player events take board + r + c (+ optional kwargs).
        kwargs.setdefault("player", player)
        try:
            result = self.func(board, r, c, **kwargs)
        except TypeError:
            # func doesn't accept r, c  (environment event)
            try:
                result = self.func(board, **kwargs)
            except TypeError:
                result = self.func(board)

        # ── Fire animation ────────────────────────────────────────────────────
        if self.anim_key and animator is not None:
            anim_method = getattr(animator, f"animate_{self.anim_key}", None)
            if anim_method:
                anim_method(result, player, done_cb)
                return

        # Fallback: no animation found, finish immediately
        done_cb()

class IdlePreviewWindow(tk.Toplevel):
    def __init__(self):
        super().__init__()
        self.name = 0

if __name__ == "__main__":
    app = App()
    app.mainloop()