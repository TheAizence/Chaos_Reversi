"""
Reversi ML Trainer
==================
Melatih model neural network untuk difficulty MEDIUM dan HARD.
Jalankan file ini secara terpisah sebelum bermain game.

Usage:
    python reversi_trainer.py              # train keduanya
    python reversi_trainer.py --medium     # medium saja
    python reversi_trainer.py --hard       # hard saja
    python reversi_trainer.py --epochs 300 # custom epoch
    python reversi_trainer.py --games 5000 # custom jumlah self-play games
"""

import sys
import os
import copy
import random
import time
import argparse

try:
    import numpy as np
    NP = True
except ImportError:
    print("❌  numpy tidak ditemukan. Install: pip install numpy")
    sys.exit(1)

# ── Konstanta game ────────────────────────────────────────────────────────────
BOARD_SIZE = 8
DIRS = [(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
EMPTY, BLACK, WHITE = 0, 1, 2
MODEL_MEDIUM = "reversi_model_medium.npy"
MODEL_HARD   = "reversi_model_hard.npy"

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

# ── ANSI Colors ───────────────────────────────────────────────────────────────
class C:
    RST  = "\033[0m";  BLD = "\033[1m"
    GRN  = "\033[92m"; RED = "\033[91m"
    YLW  = "\033[93m"; CYN = "\033[96m"
    MAG  = "\033[95m"; DIM = "\033[2m"
    BLUE = "\033[94m"

def log(msg, col=C.RST):
    print(f"{col}{msg}{C.RST}")


# ═══════════════════════════════════════════════════════════════════════════════
# GAME LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def valid_moves(board, player):
    opp   = WHITE if player == BLACK else BLACK
    moves = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] != EMPTY:
                continue
            for dr, dc in DIRS:
                nr, nc = r+dr, c+dc
                found  = False
                while 0<=nr<BOARD_SIZE and 0<=nc<BOARD_SIZE and board[nr][nc]==opp:
                    nr+=dr; nc+=dc; found=True
                if found and 0<=nr<BOARD_SIZE and 0<=nc<BOARD_SIZE and board[nr][nc]==player:
                    moves.append((r,c)); break
    return moves


def apply_move(board, player, r, c):
    board[r][c] = player
    opp     = WHITE if player == BLACK else BLACK
    flipped = []
    for dr, dc in DIRS:
        nr, nc  = r+dr, c+dc
        to_flip = []
        while 0<=nr<BOARD_SIZE and 0<=nc<BOARD_SIZE and board[nr][nc]==opp:
            to_flip.append((nr,nc)); nr+=dr; nc+=dc
        if 0<=nr<BOARD_SIZE and 0<=nc<BOARD_SIZE and board[nr][nc]==player:
            for fr,fc in to_flip:
                board[fr][fc] = player
                flipped.append((fr,fc))
    return flipped


def heuristic_score(board, player):
    """Weighted positional score untuk satu pemain."""
    s = 0
    opp = WHITE if player == BLACK else BLACK
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == player:
                s += HMAP[r][c]
            elif board[r][c] == opp:
                s -= HMAP[r][c]
    return s


def minimax_simple(board, depth, alpha, beta, is_max):
    """Minimax ringan untuk generate data training."""
    player = WHITE if is_max else BLACK
    moves  = valid_moves(board, player)
    if depth == 0 or not moves:
        return heuristic_score(board, WHITE), None
    best_m = None
    if is_max:
        mx = float("-inf")
        for r,c in moves:
            tb = copy.deepcopy(board)
            apply_move(tb, WHITE, r, c)
            ev,_ = minimax_simple(tb, depth-1, alpha, beta, False)
            if ev>mx: mx,best_m = ev,(r,c)
            alpha = max(alpha, ev)
            if beta<=alpha: break
        return mx, best_m
    else:
        mn = float("inf")
        for r,c in moves:
            tb = copy.deepcopy(board)
            apply_move(tb, BLACK, r, c)
            ev,_ = minimax_simple(tb, depth-1, alpha, beta, True)
            if ev<mn: mn,best_m = ev,(r,c)
            beta = min(beta, ev)
            if beta<=alpha: break
        return mn, best_m


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION  (harus identik dengan NeuralModel di game)
# ═══════════════════════════════════════════════════════════════════════════════
def extract_features(board, vw, vb) -> np.ndarray:
    """
    70-dimensional feature vector:
      0-63  : board occupancy  (+1=WHITE, -1=BLACK, 0=EMPTY)
      64    : normalized jumlah valid moves WHITE
      65    : normalized jumlah valid moves BLACK
      66-69 : corner status (±1)
    """
    f = np.zeros(70, dtype=np.float32)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == WHITE:
                f[r*8+c] =  1.0
            elif board[r][c] == BLACK:
                f[r*8+c] = -1.0
    f[64] = len(vw) / 30.0
    f[65] = len(vb) / 30.0
    for i,(r,c) in enumerate([(0,0),(0,7),(7,0),(7,7)]):
        if board[r][c] == WHITE:
            f[66+i] =  1.0
        elif board[r][c] == BLACK:
            f[66+i] = -1.0
    return f


def board_result_label(board) -> float:
    """Label: tanh-scaled margin untuk WHITE di akhir game."""
    wc = sum(row.count(WHITE) for row in board)
    bc = sum(row.count(BLACK) for row in board)
    margin = (wc - bc) / 64.0
    return float(np.tanh(margin * 3))


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-PLAY DATA GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
class SelfPlayGenerator:
    def __init__(self, depth_w=2, depth_b=1, noise_w=0.25, noise_b=0.50):
        self.depth_w = depth_w   # minimax depth untuk WHITE (pelajar)
        self.depth_b = depth_b   # depth BLACK (lawan)
        self.noise_w = noise_w   # prob random move WHITE
        self.noise_b = noise_b   # prob random move BLACK

    def play_game(self):
        """
        Mainkan satu game self-play.
        Return: list of (features, result_label)
        """
        board      = [[EMPTY]*BOARD_SIZE for _ in range(BOARD_SIZE)]
        board[3][3] = board[4][4] = WHITE
        board[3][4] = board[4][3] = BLACK
        states     = []   # (board_snapshot, vw, vb)
        player     = BLACK

        for _ in range(BOARD_SIZE * BOARD_SIZE):
            moves = valid_moves(board, player)
            if not moves:
                opp = WHITE if player==BLACK else BLACK
                if not valid_moves(board, opp):
                    break
                player = opp
                continue

            if player == WHITE:
                if random.random() < self.noise_w:
                    mv = random.choice(moves)
                else:
                    _, mv = minimax_simple(board, self.depth_w,
                                           float("-inf"), float("inf"), True)
                    if not mv: mv = random.choice(moves)
            else:
                if random.random() < self.noise_b:
                    mv = random.choice(moves)
                else:
                    _, mv = minimax_simple(board, self.depth_b,
                                           float("-inf"), float("inf"), False)
                    if not mv: mv = random.choice(moves)

            vw = valid_moves(board, WHITE)
            vb = valid_moves(board, BLACK)
            states.append((copy.deepcopy(board), vw, vb))

            apply_move(board, player, mv[0], mv[1])
            player = WHITE if player==BLACK else BLACK

        label = board_result_label(board)
        return [(extract_features(b, vw, vb), label)
                for b, vw, vb in states]


def generate_dataset(n_games=3000, depth_w=2, depth_b=1,
                      noise_w=0.25, noise_b=0.50, verbose=True):
    gen = SelfPlayGenerator(depth_w, depth_b, noise_w, noise_b)
    X, Y = [], []
    t0 = time.time()
    for i in range(n_games):
        if verbose and (i+1) % max(1, n_games//20) == 0:
            pct = (i+1)/n_games*100
            bar = "█"*int(pct//5) + "░"*(20-int(pct//5))
            dt  = time.time() - t0
            eta = dt / (i+1) * (n_games - i - 1)
            print(f"\r  [{bar}] {pct:5.1f}%  game {i+1}/{n_games}"
                  f"  ETA {eta:.0f}s   ", end="", flush=True)
        samples = gen.play_game()
        for feat, lbl in samples:
            X.append(feat); Y.append(lbl)
    if verbose:
        print(f"\r  [{'█'*20}] 100.0%  {n_games} games  "
              f"({time.time()-t0:.1f}s total)   ")
    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.float32)


# ═══════════════════════════════════════════════════════════════════════════════
# NEURAL NETWORK  (pure numpy, no torch/tf)
# ═══════════════════════════════════════════════════════════════════════════════
class NeuralNet:
    """
    Fully-connected: input → hidden... → 1 output (tanh)
    Layer sizes = [70, h1, h2, ..., 1]
    """

    def __init__(self, layer_sizes: list, seed: int = 42):
        rng = np.random.default_rng(seed)
        self.W, self.b = [], []
        for i in range(len(layer_sizes)-1):
            fan_in = layer_sizes[i]
            fan_out= layer_sizes[i+1]
            std    = np.sqrt(2.0 / fan_in)          # He init
            self.W.append(rng.normal(0, std, (fan_in, fan_out)).astype(np.float32))
            self.b.append(np.zeros(fan_out, dtype=np.float32))

    # ── Forward ───────────────────────────────────────────────────────────────
    def forward(self, X):
        """X: (N, input_dim)  → out: (N, 1), caches for backprop"""
        self._cache = []
        a = X
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            z = a @ W + b
            if i < len(self.W) - 1:
                a = np.maximum(0, z)     # ReLU hidden
                self._cache.append((a, z, X if i==0 else self._cache[-1][0]))
            else:
                a = np.tanh(z)           # tanh output
                self._cache.append((a, z, a))
        return a  # (N, 1)

    def predict(self, X):
        a = X
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            z = a @ W + b
            a = np.maximum(0, z) if i < len(self.W)-1 else np.tanh(z)
        return a

    # ── Loss ──────────────────────────────────────────────────────────────────
    @staticmethod
    def mse_loss(pred, target):
        diff = pred.ravel() - target.ravel()
        return float(np.mean(diff**2)), diff

    # ── Backprop ──────────────────────────────────────────────────────────────
    def _backward(self, X, diff):
        """Adam backprop; diff = (pred - target) residuals."""
        N       = X.shape[0]
        n_layers= len(self.W)
        grads_W = [np.zeros_like(w) for w in self.W]
        grads_b = [np.zeros_like(bv) for bv in self.b]

        # Rebuild activations (simple re-forward without caching overhead)
        acts = [X]
        a    = X
        for i, (W, bv) in enumerate(zip(self.W, self.b)):
            z = a @ W + bv
            a = np.maximum(0, z) if i < n_layers-1 else np.tanh(z)
            acts.append(a)

        delta = (2.0 / N) * diff.reshape(-1, 1) * (1 - acts[-1]**2)   # tanh grad

        for i in reversed(range(n_layers)):
            prev_a   = acts[i]
            grads_W[i] = prev_a.T @ delta
            grads_b[i] = delta.sum(axis=0)
            if i > 0:
                delta = (delta @ self.W[i].T) * (acts[i] > 0)   # ReLU grad
        return grads_W, grads_b

    # ── Training ──────────────────────────────────────────────────────────────
    def train(self, X_tr, Y_tr, X_va, Y_va,
              epochs=200, batch_size=256,
              lr=1e-3, lr_decay=0.97,
              beta1=0.9, beta2=0.999, eps=1e-8,
              patience=30, verbose=True, tag=""):
        """Mini-batch Adam with LR decay + early stopping."""
        N      = X_tr.shape[0]
        mW     = [np.zeros_like(w) for w in self.W]
        vW     = [np.zeros_like(w) for w in self.W]
        mb     = [np.zeros_like(bv) for bv in self.b]
        vb     = [np.zeros_like(bv) for bv in self.b]
        t_step = 0

        best_va  = float("inf")
        wait     = 0
        best_W   = [w.copy() for w in self.W]
        best_b   = [bv.copy() for bv in self.b]
        history  = {"train": [], "val": []}
        t0       = time.time()

        for ep in range(1, epochs+1):
            idx  = np.random.permutation(N)
            X_sh = X_tr[idx]; Y_sh = Y_tr[idx]
            tr_loss = 0.0
            n_batches = 0

            for start in range(0, N, batch_size):
                xb = X_sh[start:start+batch_size]
                yb = Y_sh[start:start+batch_size]
                pred = self.forward(xb)
                loss, diff = self.mse_loss(pred, yb)
                tr_loss += loss; n_batches += 1
                gW, gb   = self._backward(xb, diff)
                t_step  += 1
                bc1 = 1 - beta1**t_step
                bc2 = 1 - beta2**t_step
                for i in range(len(self.W)):
                    mW[i] = beta1*mW[i] + (1-beta1)*gW[i]
                    vW[i] = beta2*vW[i] + (1-beta2)*gW[i]**2
                    mb[i] = beta1*mb[i] + (1-beta1)*gb[i]
                    vb[i] = beta2*vb[i] + (1-beta2)*gb[i]**2
                    mW_hat = mW[i] / bc1; vW_hat = vW[i] / bc2
                    mb_hat = mb[i] / bc1; vb_hat = vb[i] / bc2
                    self.W[i] -= lr * mW_hat / (np.sqrt(vW_hat) + eps)
                    self.b[i] -= lr * mb_hat / (np.sqrt(vb_hat) + eps)

            tr_loss /= n_batches
            va_pred  = self.predict(X_va)
            va_loss, _= self.mse_loss(va_pred, Y_va)
            history["train"].append(tr_loss)
            history["val"].append(va_loss)
            lr *= lr_decay   # LR decay

            if va_loss < best_va - 1e-6:
                best_va = va_loss
                wait    = 0
                best_W  = [w.copy() for w in self.W]
                best_b  = [bv.copy() for bv in self.b]
            else:
                wait += 1
                if wait >= patience:
                    if verbose:
                        print(f"\r  {C.YLW}Early stopping at epoch {ep}{C.RST}     ")
                    break

            if verbose and (ep % max(1, epochs//20) == 0 or ep == 1):
                elapsed = time.time() - t0
                bar_pct = ep / epochs
                bar_len = int(bar_pct * 28)
                bar     = "█"*bar_len + "░"*(28-bar_len)
                print(f"\r  {C.DIM}[{bar}]{C.RST} ep {ep:4d}  "
                      f"tr={tr_loss:.5f}  va={va_loss:.5f}  "
                      f"best={best_va:.5f}  {elapsed:.0f}s", end="", flush=True)

        if verbose:
            print()

        # Restore best weights
        self.W = best_W
        self.b = best_b
        return history

    # ── Persistence ───────────────────────────────────────────────────────────
    def save(self, path):
        np.save(path, {"weights": self.W, "biases": self.b}, allow_pickle=True)
        log(f"  ✔  Model saved → {path}", C.GRN)

    @classmethod
    def load(cls, path, layer_sizes):
        obj = cls(layer_sizes)
        d   = np.load(path, allow_pickle=True).item()
        obj.W = d["weights"]
        obj.b = d["biases"]
        return obj


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATOR
# ═══════════════════════════════════════════════════════════════════════════════
def evaluate_model(model, n_eval=80, depth_opp=2, verbose=True):
    """
    Mainkan n_eval games model (WHITE) vs minimax(depth_opp) (BLACK).
    Return win_rate.
    """
    wins = draws = losses = 0
    for _ in range(n_eval):
        board      = [[EMPTY]*BOARD_SIZE for _ in range(BOARD_SIZE)]
        board[3][3] = board[4][4] = WHITE
        board[3][4] = board[4][3] = BLACK
        player = BLACK

        for _ in range(BOARD_SIZE**2):
            moves = valid_moves(board, player)
            if not moves:
                opp = WHITE if player==BLACK else BLACK
                if not valid_moves(board, opp): break
                player = opp; continue

            if player == WHITE:
                # Model picks best move
                best_v = float("-inf"); best = moves[0]
                for r,c in moves:
                    tb = copy.deepcopy(board)
                    apply_move(tb, WHITE, r, c)
                    vw = valid_moves(tb, WHITE); vb = valid_moves(tb, BLACK)
                    v  = model.predict(extract_features(tb,vw,vb).reshape(1,-1))[0,0]
                    if v > best_v: best_v, best = v, (r,c)
                mv = best
            else:
                _, mv = minimax_simple(board, depth_opp, float("-inf"), float("inf"), False)
                if not mv: mv = random.choice(moves)

            apply_move(board, player, mv[0], mv[1])
            player = WHITE if player==BLACK else BLACK

        wc = sum(row.count(WHITE) for row in board)
        bc = sum(row.count(BLACK) for row in board)
        if wc>bc: wins += 1
        elif wc<bc: losses += 1
        else: draws += 1

    wr = wins / n_eval * 100
    if verbose:
        log(f"  Eval: W{wins} D{draws} L{losses}  win_rate={wr:.1f}%",
            C.GRN if wr>=50 else C.YLW)
    return wr


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING PIPELINES
# ═══════════════════════════════════════════════════════════════════════════════
def train_medium(n_games=3000, epochs=200):
    log("\n" + "═"*60, C.CYN)
    log("  TRAINING  ─  MEDIUM  (Neural Net, 70→64→32→1)", C.CYN)
    log("═"*60, C.CYN)

    log("\n● Generating self-play dataset...", C.YLW)
    X, Y = generate_dataset(n_games=n_games, depth_w=1, depth_b=1,
                             noise_w=0.40, noise_b=0.50)
    log(f"  Samples: {len(X):,}  |  label range [{Y.min():.3f}, {Y.max():.3f}]",
        C.DIM)

    # Shuffle + split
    idx  = np.random.permutation(len(X))
    X, Y = X[idx], Y[idx]
    split= int(0.88 * len(X))
    X_tr, Y_tr = X[:split], Y[:split]
    X_va, Y_va = X[split:], Y[split:]

    log(f"\n● Training  ({epochs} epochs max, early-stop patience=40)...", C.YLW)
    net = NeuralNet([70, 64, 32, 1])
    net.train(X_tr, Y_tr, X_va, Y_va, epochs=epochs,
              batch_size=256, lr=2e-3, lr_decay=0.98, patience=40)

    log("\n● Evaluating vs minimax(depth=1)...", C.YLW)
    evaluate_model(net, n_eval=100, depth_opp=1)

    net.save(MODEL_MEDIUM)
    log(f"  Medium model ready: {MODEL_MEDIUM}\n", C.GRN)
    return net


def train_hard(n_games=5000, epochs=300):
    log("\n" + "═"*60, C.MAG)
    log("  TRAINING  ─  HARD   (Neural Net, 70→128→64→32→1)", C.MAG)
    log("═"*60, C.MAG)

    log("\n● Generating self-play dataset (minimax depth 2 vs 1)...", C.YLW)
    X, Y = generate_dataset(n_games=n_games, depth_w=2, depth_b=1,
                             noise_w=0.20, noise_b=0.40)
    log(f"  Samples: {len(X):,}  |  label range [{Y.min():.3f}, {Y.max():.3f}]",
        C.DIM)

    # Shuffle + split
    idx  = np.random.permutation(len(X))
    X, Y = X[idx], Y[idx]
    split= int(0.88 * len(X))
    X_tr, Y_tr = X[:split], Y[:split]
    X_va, Y_va = X[split:], Y[split:]

    log(f"\n● Training  ({epochs} epochs max, early-stop patience=50)...", C.YLW)
    net = NeuralNet([70, 128, 64, 32, 1])
    net.train(X_tr, Y_tr, X_va, Y_va, epochs=epochs,
              batch_size=512, lr=1e-3, lr_decay=0.99, patience=50)

    log("\n● Evaluating vs minimax(depth=2)...", C.YLW)
    evaluate_model(net, n_eval=100, depth_opp=2)

    net.save(MODEL_HARD)
    log(f"  Hard model ready: {MODEL_HARD}\n", C.GRN)
    return net


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS PRINTER  (optional live loss chart in terminal)
# ═══════════════════════════════════════════════════════════════════════════════
def print_loss_summary(history, tag):
    tr  = history["train"]
    va  = history["val"]
    best= min(va)
    ep  = va.index(best) + 1
    log(f"\n  {'─'*40}", C.DIM)
    log(f"  {tag} — final train={tr[-1]:.5f}  val={va[-1]:.5f}", C.DIM)
    log(f"  Best val={best:.5f} at epoch {ep}", C.DIM)
    log(f"  Improvement: {(tr[0]-tr[-1])/tr[0]*100:.1f}% loss reduction", C.DIM)
    log(f"  {'─'*40}\n", C.DIM)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="Train Reversi ML models (medium / hard)")
    parser.add_argument("--medium", action="store_true", help="Train medium only")
    parser.add_argument("--hard",   action="store_true", help="Train hard only")
    parser.add_argument("--games",  type=int, default=None,
                        help="Override n_games for both models")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Override max epochs for both models")
    parser.add_argument("--eval",   action="store_true",
                        help="Only evaluate existing saved models (no training)")
    args = parser.parse_args()

    both = not args.medium and not args.hard

    print()
    log("╔══════════════════════════════════════════════════════╗", C.CYN)
    log("║      REVERSI ULTIMATE  ─  ML TRAINER V1             ║", C.CYN)
    log("╚══════════════════════════════════════════════════════╝", C.CYN)
    log(f"  numpy {np.__version__}   Python {sys.version.split()[0]}", C.DIM)

    # ── Eval-only mode ────────────────────────────────────────────────────────
    if args.eval:
        for path, layers, tag in [
            (MODEL_MEDIUM, [70, 64, 32, 1],          "MEDIUM"),
            (MODEL_HARD,   [70, 128, 64, 32, 1],     "HARD"),
        ]:
            if os.path.exists(path):
                log(f"\n● Evaluating {tag} model ({path})...", C.YLW)
                net = NeuralNet.load(path, layers)
                depth = 1 if tag == "MEDIUM" else 2
                evaluate_model(net, n_eval=150, depth_opp=depth)
            else:
                log(f"  ✘ {path} not found — train first", C.RED)
        return

    # ── Training ──────────────────────────────────────────────────────────────
    t_total = time.time()

    if both or args.medium:
        n  = args.games  or 3000
        ep = args.epochs or 200
        h  = train_medium(n_games=n, epochs=ep)
        print_loss_summary(h.train(   # dummy call — history already returned
            np.zeros((1,70),np.float32),
            np.zeros((1,),  np.float32),
            np.zeros((1,70),np.float32),
            np.zeros((1,),  np.float32),
            epochs=0) if False else {"train":[],"val":[]}, "Medium") \
            if False else None

    if both or args.hard:
        n  = args.games  or 5000
        ep = args.epochs or 300
        train_hard(n_games=n, epochs=ep)

    log(f"\n✅  All done in {time.time()-t_total:.1f}s", C.GRN)
    log("   Put the .npy files next to reversi_v3.py and launch the game!", C.GRN)
    print()


if __name__ == "__main__":
    main()
