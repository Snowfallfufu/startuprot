"""
Beat the Dealer Calculator (Polished UI Edition)
------------------------------------------------------
A fun, PLAY-MONEY-ONLY calculator game.

Rules:
  - Tap digits/operators on the on-screen keypad to build an expression.
  - Hit "=" to lock in the calculation. A POPUP appears (centered on the
    window) with two choices:
      a) Pay 25 coins to unlock instantly, or
      b) Play ONE round of Blackjack against the dealer.
         - You may only play Blackjack ONCE per calculation.
         - Win / Blackjack -> unlocks for FREE.
         - Push (tie)      -> the Answer Locked popup reappears (pay-only,
                               since your one Blackjack try is used).
         - Lose / Bust     -> you are automatically charged 25 coins, and
                               the Answer Locked popup reappears (pay-only).
  - The revealed answer is intentionally off by 1, just for fun.

No real money, no real payments, no network calls. Everything is local
and just for entertainment. Run this file directly in PyCharm
(Run > Run 'beat_the_dealer_calculator').
"""

import tkinter as tk
from tkinter import messagebox
import random

STARTING_BALANCE = 100
UNLOCK_COST = 25

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["♠", "♥", "♦", "♣"]
RED_SUITS = {"♥", "♦"}

# ---------- Palette ----------
BG = "#14141f"
PANEL = "#1c1c2b"
DISPLAY_BG = "#0d0d16"
ACCENT_GOLD = "#f2c94c"
ACCENT_BLUE = "#4c8cf2"
ACCENT_PURPLE = "#9b6cf2"
ACCENT_ORANGE = "#f2954c"
ACCENT_RED = "#f25c5c"
ACCENT_GREEN = "#4cd97b"
TEXT_MAIN = "#f2f2f7"
TEXT_MUTED = "#8b8ba0"
KEY_NUM = "#2a2a40"
KEY_OP = "#3a3a58"
FELT = "#0e2e22"

FONT_TITLE = ("Segoe UI", 19, "bold")
FONT_SUB = ("Segoe UI", 9)
FONT_BALANCE = ("Segoe UI", 13, "bold")
FONT_DISPLAY = ("Consolas", 22)
FONT_RESULT = ("Segoe UI", 21, "bold")
FONT_KEY = ("Segoe UI", 14, "bold")
FONT_STATUS = ("Segoe UI", 10)


def card_value(rank):
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(cards):
    total = sum(card_value(rank) for rank, _ in cards)
    aces = sum(1 for rank, _ in cards if rank == "A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def draw_card():
    return (random.choice(RANKS), random.choice(SUITS))


def center_on_parent(win, parent, width, height):
    win.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    x = px + (pw - width) // 2
    y = py + (ph - height) // 2
    win.geometry(f"{width}x{height}+{x}+{y}")


def make_hover_button(parent, text, base_bg, hover_bg, fg, font, command, width=None, height=None, **kw):
    btn = tk.Button(
        parent, text=text, font=font, bg=base_bg, fg=fg,
        activebackground=hover_bg, activeforeground=fg,
        relief="flat", bd=0, cursor="hand2",
        command=command, **({"width": width} if width else {}),
        **({"height": height} if height else {})
    )
    if kw.get("highlight", True):
        btn.configure(highlightthickness=0)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=base_bg))
    return btn


def make_card_widget(parent, rank, suit):
    is_red = suit in RED_SUITS
    color = "#e05c5c" if is_red else "#eaeaea"
    frame = tk.Frame(parent, bg="white", width=46, height=64, highlightthickness=1,
                      highlightbackground="#cccccc")
    frame.pack_propagate(False)
    top = tk.Label(frame, text=rank, font=("Segoe UI", 11, "bold"), bg="white",
                   fg="#c0392b" if is_red else "#222222")
    top.pack(anchor="nw", padx=4, pady=(2, 0))
    mid = tk.Label(frame, text=suit, font=("Segoe UI", 18), bg="white",
                   fg="#c0392b" if is_red else "#222222")
    mid.pack(expand=True)
    return frame


def make_hidden_card_widget(parent):
    frame = tk.Frame(parent, bg="#2e2e55", width=46, height=64, highlightthickness=1,
                      highlightbackground="#4a4a75")
    frame.pack_propagate(False)
    tk.Label(frame, text="🂠", font=("Segoe UI", 22), bg="#2e2e55", fg="#8b8bd6").pack(expand=True)
    return frame


class CalculatorGame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Beat the Dealer Calculator")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.balance = STARTING_BALANCE
        self.expression = ""
        self.computed_answer = None
        self.unlocked = False
        self.dealer_attempt_used = False

        self._build_ui()

        # Size the window to whatever it actually needs, instead of guessing
        # fixed pixel dimensions (fonts render at different widths per OS).
        self.update_idletasks()
        w = self.winfo_reqwidth() + 20
        h = self.winfo_reqheight() + 20
        self.geometry(f"{w}x{h}")

    # ---------- UI ----------
    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", pady=(22, 6))

        tk.Label(
            header, text="🎲 Beat the Dealer", font=FONT_TITLE,
            fg=ACCENT_GOLD, bg=BG
        ).pack()

        tk.Label(
            header, text="play-money calculator  ·  nothing here is real currency",
            font=FONT_SUB, fg=TEXT_MUTED, bg=BG
        ).pack(pady=(2, 0))

        # Balance badge
        balance_frame = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground="#2e2e44")
        balance_frame.pack(pady=(16, 14))
        self.balance_var = tk.StringVar()
        self._update_balance_label()
        tk.Label(
            balance_frame, textvariable=self.balance_var, font=FONT_BALANCE,
            fg=ACCENT_GREEN, bg=PANEL, padx=18, pady=8
        ).pack()

        # Display panel
        display_panel = tk.Frame(self, bg=DISPLAY_BG, highlightthickness=1,
                                  highlightbackground="#2e2e44")
        display_panel.pack(padx=24, fill="x")

        self.expr_var = tk.StringVar(value="0")
        tk.Label(
            display_panel, textvariable=self.expr_var, font=FONT_DISPLAY,
            fg=TEXT_MUTED, bg=DISPLAY_BG, anchor="e", padx=16
        ).pack(fill="x", pady=(14, 2))

        self.result_var = tk.StringVar(value="🔒 Locked")
        tk.Label(
            display_panel, textvariable=self.result_var, font=FONT_RESULT,
            fg=ACCENT_GOLD, bg=DISPLAY_BG, anchor="e", padx=16,
            wraplength=380, justify="right"
        ).pack(fill="x", pady=(0, 14))

        # Keypad
        keypad_frame = tk.Frame(self, bg=BG)
        keypad_frame.pack(pady=20)

        rows = [
            [("7", "num"), ("8", "num"), ("9", "num"), ("/", "op")],
            [("4", "num"), ("5", "num"), ("6", "num"), ("*", "op")],
            [("1", "num"), ("2", "num"), ("3", "num"), ("-", "op")],
            [("0", "num"), (".", "num"), ("C", "clear"), ("+", "op")],
            [("(", "op"), (")", "op"), ("⌫", "clear"), ("=", "equals")],
        ]

        style_map = {
            "num": (KEY_NUM, "#3a3a58"),
            "op": (KEY_OP, "#4d4d78"),
            "clear": ("#4a2c2c", "#6b3a3a"),
            "equals": (ACCENT_BLUE, "#6ba3f5"),
        }

        for r, row in enumerate(rows):
            for c, (label, kind) in enumerate(row):
                base, hover = style_map[kind]
                fg = TEXT_MAIN
                btn = make_hover_button(
                    keypad_frame, label, base, hover, fg, FONT_KEY,
                    lambda l=label: self.on_key(l), width=5, height=2
                )
                btn.grid(row=r, column=c, padx=5, pady=5)

        # Status line
        self.status_var = tk.StringVar(value="")
        tk.Label(
            self, textvariable=self.status_var, font=FONT_STATUS,
            fg=TEXT_MUTED, bg=BG, wraplength=390, justify="center"
        ).pack(pady=(4, 10))

        reset_btn = make_hover_button(
            self, "Reset Balance", "#2a2a3d", "#3a3a52", TEXT_MUTED,
            ("Segoe UI", 9), self.reset_balance, width=16
        )
        reset_btn.pack(pady=(0, 10))

    def _update_balance_label(self):
        self.balance_var.set(f"🪙  {self.balance}  coins")

    # ---------- Keypad logic ----------
    def on_key(self, key):
        if key == "C":
            self.expression = ""
            self.expr_var.set("0")
            self._lock_again()
            return

        if key == "⌫":
            self.expression = self.expression[:-1]
            self.expr_var.set(self.expression if self.expression else "0")
            return

        if key == "=":
            self.calculate()
            return

        self.expression += key
        self.expr_var.set(self.expression)

    def _lock_again(self):
        self.unlocked = False
        self.computed_answer = None
        self.dealer_attempt_used = False
        self.result_var.set("🔒 Locked")
        self.status_var.set("")

    def calculate(self):
        expr = self.expression.strip()
        if not expr:
            messagebox.showwarning("Empty input", "Tap some numbers first.")
            return

        try:
            allowed = set("0123456789+-*/(). ")
            if not set(expr) <= allowed:
                raise ValueError("Only numbers and + - * / ( ) are allowed.")
            answer = eval(expr, {"__builtins__": {}}, {})
        except Exception:
            messagebox.showerror("Invalid expression", "That's not a valid expression. Try again.")
            return

        self.computed_answer = answer
        self.unlocked = False
        self.dealer_attempt_used = False

        self.result_var.set("🔒 Locked")
        self.status_var.set("Answer locked.")

        self.show_unlock_popup()

    def _format(self, value):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _reveal(self):
        wrong_answer = self.computed_answer + 1  # intentionally off by 1
        self.unlocked = True
        self.result_var.set(f"✅ {self._format(wrong_answer)}")

        # Auto-clear the input so the next calculation starts fresh
        self.expression = ""
        self.expr_var.set("0")

    def show_unlock_popup(self):
        if self.unlocked or self.computed_answer is None:
            return
        UnlockPopup(self, show_dealer_option=not self.dealer_attempt_used)

    def pay_to_unlock(self):
        if self.unlocked or self.computed_answer is None:
            return
        if self.balance < UNLOCK_COST:
            messagebox.showinfo("Not enough coins", "You don't have enough coins.")
            return

        self.balance -= UNLOCK_COST
        self._update_balance_label()
        self._reveal()
        self.status_var.set(f"Paid {UNLOCK_COST} coins to unlock.")

    # ---------- Blackjack ----------
    def start_blackjack(self):
        if self.unlocked or self.computed_answer is None:
            return
        if self.dealer_attempt_used:
            return

        self.dealer_attempt_used = True
        BlackjackWindow(self)

    def resolve_blackjack(self, outcome):
        if outcome == "win":
            self._reveal()
            self.status_var.set("🎉 Blackjack win! Answer unlocked for free.")
        elif outcome == "push":
            self.status_var.set("🤝 Push (tie). No charge, but still locked.")
            self.show_unlock_popup()
        else:  # lose
            charge = min(UNLOCK_COST, self.balance)
            self.balance -= charge
            if self.balance < 0:
                self.balance = 0
            self._update_balance_label()
            self.status_var.set(f"😞 Lost to the dealer. Charged {charge} coins automatically.")

            if self.balance <= 0:
                messagebox.showinfo("Out of coins", "You're out of coins! Resetting balance for more fun.")
                self.reset_balance()

            self.show_unlock_popup()

    def reset_balance(self):
        self.balance = STARTING_BALANCE
        self._update_balance_label()
        messagebox.showinfo("Balance reset", f"Balance reset to {STARTING_BALANCE} coins.")


class UnlockPopup(tk.Toplevel):
    """Popup shown after calculating (or after a Blackjack loss/push)."""

    def __init__(self, app: CalculatorGame, show_dealer_option: bool):
        super().__init__(app)
        self.app = app
        self.title("Answer Locked")
        self.resizable(False, False)
        self.configure(bg=PANEL)
        self.transient(app)

        tk.Label(
            self, text="🔒 Your answer is locked!", font=("Segoe UI", 15, "bold"),
            fg=ACCENT_GOLD, bg=PANEL
        ).pack(pady=(24, 8), padx=24)

        tk.Label(
            self, text="Choose how to unlock it:", font=("Segoe UI", 11),
            fg=TEXT_MAIN, bg=PANEL
        ).pack(pady=(0, 18), padx=24)

        pay_btn = make_hover_button(
            self, f"💰  Pay {UNLOCK_COST} coins", ACCENT_ORANGE, "#f5ab6e", "#1a1a1a",
            ("Segoe UI", 12, "bold"), self._choose_pay, height=2
        )
        pay_btn.pack(pady=6, padx=24, fill="x")

        if show_dealer_option:
            dealer_btn = make_hover_button(
                self, "🃏  Beat the Dealer — Blackjack (1 try)", ACCENT_PURPLE, "#b493f7", "#1a1a1a",
                ("Segoe UI", 12, "bold"), self._choose_dealer, height=2
            )
            dealer_btn.pack(pady=6, padx=24, fill="x")

        make_hover_button(
            self, "Maybe later", PANEL, "#2a2a3d", TEXT_MUTED,
            ("Segoe UI", 9), self.destroy, width=14
        ).pack(pady=(18, 5))

        # Size the popup to whatever its content actually needs, instead of
        # guessing fixed pixel dimensions (button text width varies by OS/font).
        self.update_idletasks()
        width = self.winfo_reqwidth() + 20
        height = self.winfo_reqheight() + 20
        center_on_parent(self, app, width, height)
        self.grab_set()

    def _choose_pay(self):
        self.destroy()
        self.app.pay_to_unlock()

    def _choose_dealer(self):
        self.destroy()
        self.app.start_blackjack()


class BlackjackWindow(tk.Toplevel):
    """A one-round Blackjack game with card-styled hands."""

    def __init__(self, app: CalculatorGame):
        super().__init__(app)
        self.app = app
        self.title("Blackjack — Beat the Dealer")
        self.resizable(False, False)
        self.configure(bg=FELT)
        self.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        self.player_cards = [draw_card(), draw_card()]
        self.dealer_cards = [draw_card(), draw_card()]
        self.game_over = False

        self._build_ui()
        self._refresh(reveal_dealer=False)

        # Size the window to fit its actual content instead of a fixed guess.
        self.update_idletasks()
        w = self.winfo_reqwidth() + 20
        h = self.winfo_reqheight() + 20
        center_on_parent(self, app, w, h)
        self.grab_set()

        if hand_value(self.player_cards) == 21:
            self._finish()

    def _autosize(self):
        """Recompute window size so a growing hand (from Hit) never gets clipped."""
        self.update_idletasks()
        w = self.winfo_reqwidth() + 20
        h = self.winfo_reqheight() + 20
        x = self.winfo_x()
        y = self.winfo_y()
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        tk.Label(
            self, text="🂡 Blackjack", font=("Segoe UI", 17, "bold"),
            fg=ACCENT_GOLD, bg=FELT
        ).pack(pady=(18, 2))

        tk.Label(
            self, text="one attempt only", font=("Segoe UI", 9, "italic"),
            fg="#8fd6b4", bg=FELT
        ).pack(pady=(0, 14))

        # Dealer section
        tk.Label(self, text="DEALER", font=("Segoe UI", 10, "bold"),
                 fg="#8fd6b4", bg=FELT).pack()
        self.dealer_cards_frame = tk.Frame(self, bg=FELT)
        self.dealer_cards_frame.pack(pady=(4, 4))
        self.dealer_value_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.dealer_value_var, font=("Segoe UI", 10),
                 fg=TEXT_MUTED, bg=FELT).pack(pady=(0, 14))

        # Player section
        tk.Label(self, text="YOU", font=("Segoe UI", 10, "bold"),
                 fg="#8fd6b4", bg=FELT).pack()
        self.player_cards_frame = tk.Frame(self, bg=FELT)
        self.player_cards_frame.pack(pady=(4, 4))
        self.player_value_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.player_value_var, font=("Segoe UI", 10),
                 fg=TEXT_MUTED, bg=FELT).pack(pady=(0, 10))

        self.status_label = tk.Label(
            self, text="Hit or Stand?", font=("Segoe UI", 12, "bold"),
            fg=ACCENT_GOLD, bg=FELT
        )
        self.status_label.pack(pady=10)

        btn_frame = tk.Frame(self, bg=FELT)
        btn_frame.pack(pady=8)

        self.hit_btn = make_hover_button(
            btn_frame, "Hit", ACCENT_BLUE, "#6ba3f5", "#0d0d16",
            ("Segoe UI", 12, "bold"), self.hit, width=10, height=1
        )
        self.hit_btn.grid(row=0, column=0, padx=8)

        self.stand_btn = make_hover_button(
            btn_frame, "Stand", ACCENT_RED, "#f58686", "#0d0d16",
            ("Segoe UI", 12, "bold"), self.stand, width=10, height=1
        )
        self.stand_btn.grid(row=0, column=1, padx=8)

        self.close_btn = make_hover_button(
            self, "Close", "#1e3d30", "#2a5240", "#8fd6b4",
            ("Segoe UI", 9), self.destroy, width=12
        )
        self.close_btn.pack(pady=(16, 10))
        self.close_btn.config(state="disabled")

    def _on_close_attempt(self):
        if not self.game_over:
            messagebox.showwarning("Finish the round", "Finish this Blackjack round first — it's your only attempt!")
            return
        self.destroy()

    def _render_hand(self, frame, cards, hide_last=False):
        for widget in frame.winfo_children():
            widget.destroy()
        for i, (rank, suit) in enumerate(cards):
            if hide_last and i == len(cards) - 1:
                card_widget = make_hidden_card_widget(frame)
            else:
                card_widget = make_card_widget(frame, rank, suit)
            card_widget.pack(side="left", padx=4)

    def _refresh(self, reveal_dealer):
        self._render_hand(self.dealer_cards_frame, self.dealer_cards, hide_last=not reveal_dealer)
        self._render_hand(self.player_cards_frame, self.player_cards)

        if reveal_dealer:
            self.dealer_value_var.set(f"value: {hand_value(self.dealer_cards)}")
        else:
            self.dealer_value_var.set("value: ?")

        self.player_value_var.set(f"value: {hand_value(self.player_cards)}")

    def hit(self):
        if self.game_over:
            return
        self.player_cards.append(draw_card())
        value = hand_value(self.player_cards)
        self._refresh(reveal_dealer=False)
        self._autosize()

        if value > 21:
            self._finish()
        elif value == 21:
            self.stand()

    def stand(self):
        if self.game_over:
            return
        self._finish()

    def _finish(self):
        self.game_over = True
        self.hit_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")

        player_value = hand_value(self.player_cards)

        if player_value > 21:
            self._refresh(reveal_dealer=True)
            self._autosize()
            self.status_label.config(text="💥 You busted! Dealer wins.", fg=ACCENT_RED)
            outcome = "lose"
        else:
            while hand_value(self.dealer_cards) < 17:
                self.dealer_cards.append(draw_card())

            self._refresh(reveal_dealer=True)
            self._autosize()
            dealer_value = hand_value(self.dealer_cards)

            if dealer_value > 21:
                self.status_label.config(text="🎉 Dealer busts! You win!", fg=ACCENT_GREEN)
                outcome = "win"
            elif player_value > dealer_value:
                self.status_label.config(text=f"🎉 You win! {player_value} vs {dealer_value}", fg=ACCENT_GREEN)
                outcome = "win"
            elif player_value < dealer_value:
                self.status_label.config(text=f"😞 Dealer wins. {dealer_value} vs {player_value}", fg=ACCENT_RED)
                outcome = "lose"
            else:
                self.status_label.config(text=f"🤝 Push! Both have {player_value}", fg=ACCENT_GOLD)
                outcome = "push"

        self.close_btn.config(state="normal")
        self.app.resolve_blackjack(outcome)


if __name__ == "__main__":
    app = CalculatorGame()
    app.mainloop()