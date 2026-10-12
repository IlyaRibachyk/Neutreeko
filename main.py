"""
Нейтріко (Neutreeko) — структура гри.
Лише класи, властивості та методи; логіка поки не реалізована.

Правила (коротко):
- дошка 5x5, у кожного гравця по 3 фішки;
- хід = фішка ковзає по прямій (8 напрямків) до перешкоди (край дошки або інша фішка);
- перемога: три власні фішки в ряд (горизонталь, вертикаль, діагональ);
- нічия: одна й та сама позиція повторилась 3 рази.
"""

from __future__ import annotations

import random
import threading
import time
import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

# ======================================================================
# Константи та перелічення
# ======================================================================

BOARD_SIZE = 5
PIECES_PER_PLAYER = 3

DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


class PlayerColor(Enum):
    """Колір гравця."""

    BLACK = 1
    WHITE = 2


class Difficulty(Enum):
    """Рівні складності."""

    EASY = 1
    MEDIUM = 2
    HARD = 3


class GameStatus(Enum):
    """Стан гри."""

    IN_PROGRESS = 1
    BLACK_WON = 2
    WHITE_WON = 3
    DRAW = 4


class GameMode(Enum):
    """Режим гри."""

    HUMAN_VS_AI = 1
    HUMAN_VS_HUMAN = 2


COLOR_NAMES = {PlayerColor.BLACK: "Чорні", PlayerColor.WHITE: "Білі"}
DIFFICULTY_NAMES = {
    Difficulty.EASY: "Легкий",
    Difficulty.MEDIUM: "Середній",
    Difficulty.HARD: "Складний",
}
RESULT_TEXTS = {
    GameStatus.BLACK_WON: "Перемогли чорні!",
    GameStatus.WHITE_WON: "Перемогли білі!",
    GameStatus.DRAW: "Нічия (позиція повторилась тричі)!",
}

# Початкова розстановка (рядок, стовпець), нумерація з 0
START_BLACK = [(1, 2), (4, 1), (4, 3)]  # C2, B5, D5
START_WHITE = [(0, 1), (0, 3), (3, 2)]  # B1, D1, C4


# ======================================================================
# Модель (логіка гри)
# ======================================================================


@dataclass(frozen=True)
class Position:
    """Клітинка дошки."""

    row: int
    col: int

    def is_valid(self) -> bool:
        """Чи знаходиться клітинка в межах дошки."""
        return 0 <= self.row < BOARD_SIZE and 0 <= self.col < BOARD_SIZE

    def shifted(self, d_row: int, d_col: int) -> Position:
        """Повертає нову позицію зі зсувом."""
        return Position(self.row + d_row, self.col + d_col)


@dataclass(frozen=True)
class Move:
    """Хід: з якої клітинки в яку."""

    start: Position
    end: Position


@dataclass
class Piece:
    """Фішка."""

    color: PlayerColor
    position: Position


class Board:
    """Ігрова дошка 5x5 та розташування фішок."""

    def __init__(self) -> None:
        self.size: int = BOARD_SIZE
        self.grid: list[list[Optional[PlayerColor]]] = []
        self.reset()

    def reset(self) -> None:
        """Розставляє фішки у початкову позицію."""
        self.grid = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        for r, c in START_BLACK:
            self.grid[r][c] = PlayerColor.BLACK
        for r, c in START_WHITE:
            self.grid[r][c] = PlayerColor.WHITE

    def get(self, pos: Position) -> Optional[PlayerColor]:
        """Повертає колір фішки в клітинці або None, якщо вона порожня."""
        if not pos.is_valid():
            return None
        return self.grid[pos.row][pos.col]

    def is_empty(self, pos: Position) -> bool:
        """Чи порожня клітинка."""
        return pos.is_valid() and self.grid[pos.row][pos.col] is None

    def get_pieces(self, color: PlayerColor) -> list[Piece]:
        """Усі фішки гравця."""
        return [
            Piece(color, Position(r, c))
            for r in range(BOARD_SIZE)
            for c in range(BOARD_SIZE)
            if self.grid[r][c] == color
        ]

    def apply_move(self, move: Move) -> None:
        """Виконує хід на дошці."""
        color = self.grid[move.start.row][move.start.col]
        self.grid[move.start.row][move.start.col] = None
        self.grid[move.end.row][move.end.col] = color

    def undo_move(self, move: Move) -> None:
        """Скасовує хід (потрібно для пошуку ШІ)."""
        color = self.grid[move.end.row][move.end.col]
        self.grid[move.end.row][move.end.col] = None
        self.grid[move.start.row][move.start.col] = color

    def copy(self) -> Board:
        """Глибока копія дошки."""
        new = Board()
        new.grid = [row[:] for row in self.grid]
        return new

    def to_key(self) -> tuple:
        """Незмінне представлення позиції (для підрахунку повторів)."""
        return tuple(tuple(row) for row in self.grid)


class Rules:
    """Правила гри (без стану)."""

    @staticmethod
    def slide_destination(
        board: Board, start: Position, direction: tuple[int, int]
    ) -> Optional[Position]:
        """Куди зупиниться фішка, ковзаючи у напрямку; None, якщо рухатись не можна."""
        current = start
        moved = False
        while True:
            nxt = current.shifted(*direction)
            if not board.is_empty(nxt):  # край дошки або інша фішка
                break
            current = nxt
            moved = True
        return current if moved else None

    @staticmethod
    def get_legal_moves_for_piece(board: Board, position: Position) -> list[Move]:
        """Усі допустимі ходи однієї фішки."""
        moves = []
        for direction in DIRECTIONS:
            end = Rules.slide_destination(board, position, direction)
            if end is not None:
                moves.append(Move(position, end))
        return moves

    @staticmethod
    def get_legal_moves(board: Board, color: PlayerColor) -> list[Move]:
        """Усі допустимі ходи гравця."""
        moves = []
        for piece in board.get_pieces(color):
            moves.extend(Rules.get_legal_moves_for_piece(board, piece.position))
        return moves

    @staticmethod
    def is_legal_move(board: Board, move: Move, color: PlayerColor) -> bool:
        """Перевірка допустимості ходу."""
        if board.get(move.start) != color:
            return False
        return move in Rules.get_legal_moves_for_piece(board, move.start)

    @staticmethod
    def has_three_in_row(board: Board, color: PlayerColor) -> bool:
        """Чи є в гравця три фішки в ряд."""
        return bool(Rules.find_three_in_row(board, color))

    @staticmethod
    def find_three_in_row(board: Board, color: PlayerColor) -> list[Position]:
        """Повертає три клітинки виграшної лінії або порожній список."""
        cells = {(p.position.row, p.position.col) for p in board.get_pieces(color)}
        for r, c in cells:
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                if (r + dr, c + dc) in cells and (r + 2 * dr, c + 2 * dc) in cells:
                    return [
                        Position(r, c),
                        Position(r + dr, c + dc),
                        Position(r + 2 * dr, c + 2 * dc),
                    ]
        return []


class Game:
    """Поточна партія: стан, черга ходів, історія, статус."""

    def __init__(self, mode: GameMode = GameMode.HUMAN_VS_AI) -> None:
        self.board: Board = Board()
        self.current_color: PlayerColor = PlayerColor.BLACK
        self.status: GameStatus = GameStatus.IN_PROGRESS
        self.mode: GameMode = mode
        self.move_history: list[Move] = []
        self.position_counts: dict[tuple, int] = {}
        self.winning_line: list[Position] = []

    def new_game(self) -> None:
        """Починає нову партію."""
        self.board.reset()
        self.current_color = PlayerColor.BLACK
        self.status = GameStatus.IN_PROGRESS
        self.move_history = []
        self.winning_line = []
        self.position_counts = {self._position_key(): 1}

    def make_move(self, move: Move) -> bool:
        """Виконує хід, оновлює чергу, історію й статус. False, якщо хід недопустимий."""
        if self.is_over() or not Rules.is_legal_move(
            self.board, move, self.current_color
        ):
            return False
        self.board.apply_move(move)
        self.move_history.append(move)
        self.switch_turn()
        key = self._position_key()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1
        self.update_status()
        return True

    def switch_turn(self) -> None:
        """Передає хід іншому гравцю."""
        self.current_color = (
            PlayerColor.WHITE
            if self.current_color == PlayerColor.BLACK
            else PlayerColor.BLACK
        )

    def _position_key(self) -> tuple:
        """Позиція + чий хід (для підрахунку повторів)."""
        return (self.board.to_key(), self.current_color)

    def update_status(self) -> None:
        """Перевіряє перемогу / нічию."""
        for color, status in (
            (PlayerColor.BLACK, GameStatus.BLACK_WON),
            (PlayerColor.WHITE, GameStatus.WHITE_WON),
        ):
            line = Rules.find_three_in_row(self.board, color)
            if line:
                self.status = status
                self.winning_line = line
                return
        if self.is_draw_by_repetition():
            self.status = GameStatus.DRAW
            return
        if not self.get_legal_moves():  # гравець, що ходить, не має ходів
            self.status = (
                GameStatus.WHITE_WON
                if self.current_color == PlayerColor.BLACK
                else GameStatus.BLACK_WON
            )
            return
        self.status = GameStatus.IN_PROGRESS

    def is_draw_by_repetition(self) -> bool:
        """Нічия за триразовим повторенням позиції."""
        return self.position_counts.get(self._position_key(), 0) >= 3

    def get_legal_moves(self) -> list[Move]:
        """Допустимі ходи поточного гравця."""
        return Rules.get_legal_moves(self.board, self.current_color)

    def is_over(self) -> bool:
        """Чи закінчилась гра."""
        return self.status != GameStatus.IN_PROGRESS

    def copy(self) -> Game:
        """Незалежна копія партії (для ШІ, що думає в окремому потоці)."""
        g = Game(self.mode)
        g.board = self.board.copy()
        g.current_color = self.current_color
        g.status = self.status
        g.move_history = list(self.move_history)
        g.position_counts = dict(self.position_counts)
        g.winning_line = list(self.winning_line)
        return g

    def undo_last_move(self) -> None:
        """Скасувати останній хід (опційно)."""
        if not self.move_history:
            return
        key = self._position_key()
        self.position_counts[key] = self.position_counts.get(key, 1) - 1
        self.board.undo_move(self.move_history.pop())
        self.switch_turn()
        self.status = GameStatus.IN_PROGRESS
        self.winning_line = []


# ======================================================================
# Штучний інтелект (3 рівні складності)
# ======================================================================


class SearchTimeout(Exception):
    """Вичерпано ліміт часу пошуку (внутрішній сигнал для ітеративного поглиблення)."""


def _build_search_tables():
    """Попередньо обчислені таблиці для швидкого перебору (клітинка = рядок*5 + стовпець)."""
    n = BOARD_SIZE
    rays = []  # rays[клітинка] -> список променів (по одному на напрямок)
    for r in range(n):
        for c in range(n):
            cell_rays = []
            for dr, dc in DIRECTIONS:
                ray, rr, cc = [], r + dr, c + dc
                while 0 <= rr < n and 0 <= cc < n:
                    ray.append(rr * n + cc)
                    rr, cc = rr + dr, cc + dc
                if ray:
                    cell_rays.append(tuple(ray))
            rays.append(tuple(cell_rays))

    windows = []  # усі можливі «трійки в ряд» (48 штук)
    for r in range(n):
        for c in range(n):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                r2, c2 = r + 2 * dr, c + 2 * dc
                if 0 <= r2 < n and 0 <= c2 < n:
                    windows.append((r * n + c, (r + dr) * n + c + dc, r2 * n + c2))

    by_cell = [[] for _ in range(n * n)]
    for w in windows:
        for cell in w:
            by_cell[cell].append(w)
    return tuple(rays), tuple(windows), tuple(tuple(x) for x in by_cell)


RAYS, WINDOWS, WINDOWS_BY_CELL = _build_search_tables()
_COLOR_BY_VALUE = {0: None, 1: PlayerColor.BLACK, 2: PlayerColor.WHITE}
INF = 10**9
_EXACT, _LOWER, _UPPER = 0, 1, 2  # типи записів таблиці транспозицій


class AIStrategy(ABC):
    """Базова стратегія ШІ + спільні допоміжні функції.

    Для швидкості пошук працює не з об'єктами Board, а з плоским списком
    `cells` із 25 чисел: 0 — порожньо, 1 — чорна фішка, 2 — біла фішка.
    Клітинка = рядок * 5 + стовпець; хід = пара (звідки, куди).
    """

    WIN_SCORE = 100_000
    LINE_WEIGHTS = (0, 1, 12, 100)  # «вартість» лінії з 0/1/2/3 власними фішками

    def __init__(self, color: PlayerColor) -> None:
        self.color: PlayerColor = color

    @abstractmethod
    def choose_move(self, game: Game) -> Move:
        """Обирає хід для поточної позиції."""
        pass

    # ---------------- допоміжні функції ----------------
    @staticmethod
    def board_to_cells(board: Board) -> list[int]:
        n = BOARD_SIZE
        cells = [0] * (n * n)
        for r in range(n):
            for c in range(n):
                color = board.get(Position(r, c))
                if color is not None:
                    cells[r * n + c] = color.value
        return cells

    @staticmethod
    def cells_to_key(cells: list[int], next_color_value: int) -> tuple:
        """Ключ позиції у тому ж форматі, що й Game._position_key()."""
        n = BOARD_SIZE
        rows = tuple(
            tuple(_COLOR_BY_VALUE[v] for v in cells[r * n : (r + 1) * n])
            for r in range(n)
        )
        return rows, PlayerColor(next_color_value)

    @staticmethod
    def pair_to_move(pair: tuple[int, int]) -> Move:
        n = BOARD_SIZE
        a, b = pair
        return Move(Position(a // n, a % n), Position(b // n, b % n))

    @staticmethod
    def generate_moves(cells: list[int], color: int) -> list[tuple[int, int]]:
        """Усі ходи гравця: фішка ковзає до перешкоди в кожному з напрямків."""
        moves = []
        for cell in range(len(cells)):
            if cells[cell] != color:
                continue
            for ray in RAYS[cell]:
                last = -1
                for c in ray:
                    if cells[c]:
                        break
                    last = c
                if last >= 0:
                    moves.append((cell, last))
        return moves

    @staticmethod
    def is_win(cells: list[int], color: int, cell: int) -> bool:
        """Чи утворює фішка в клітинці `cell` трійку в ряд (перевіряємо лише лінії через неї)."""
        for i, j, k in WINDOWS_BY_CELL[cell]:
            if cells[i] == color and cells[j] == color and cells[k] == color:
                return True
        return False

    def evaluate(self, cells: list[int], color: int) -> int:
        """Евристична оцінка позиції з погляду гравця `color`.

        Для кожної з 48 можливих ліній: якщо в ній немає фішок суперника —
        додаємо бали за власні фішки (чим більше, тим краще); якщо немає
        моїх — віднімаємо бали за фішки суперника.
        """
        opp = 3 - color
        w = self.LINE_WEIGHTS
        score = 0
        for i, j, k in WINDOWS:
            x, y, z = cells[i], cells[j], cells[k]
            own = (x == color) + (y == color) + (z == color)
            his = (x == opp) + (y == opp) + (z == opp)
            if his == 0:
                score += w[own]
            elif own == 0:
                score -= w[his]
        return score


class AlphaBetaStrategy(AIStrategy):
    """Альфа-бета відсікання (у формі negamax) — спільна основа всіх рівнів.

    Особливості:
    - на кожному вузлі спершу перевіряється виграш «в один хід»;
    - ітеративне поглиблення з обмеженням за часом (якщо задано time_limit);
    - таблиця транспозицій (за бажанням);
    - впорядкування ходів для кращого відсікання;
    - на корені: третє повторення позиції трактується як нічия (оцінка 0).
    """

    def __init__(
        self,
        color: PlayerColor,
        max_depth: int,
        time_limit: Optional[float] = None,
        use_transposition: bool = False,
        randomize_ties: bool = True,
    ) -> None:
        super().__init__(color)
        self.max_depth: int = max_depth
        self.time_limit: Optional[float] = time_limit
        self.use_transposition: bool = use_transposition
        self.randomize_ties: bool = (
            randomize_ties  # серед рівних за оцінкою ходів вибирати довільний
        )
        self.transposition_table: dict = {}
        self.deadline: Optional[float] = None
        self.nodes: int = 0
        self.reached_depth: int = 0

    # ------------------------------------------------------------------
    def choose_move(self, game: Game) -> Move:
        cells = self.board_to_cells(game.board)
        color = self.color.value
        root_moves = self.generate_moves(cells, color)
        if not root_moves:
            raise ValueError("Немає допустимих ходів")

        start = time.perf_counter()
        self.nodes = 0
        self.reached_depth = 0
        self.transposition_table.clear()
        ordered = list(root_moves)
        best_moves = [root_moves[0]]

        for depth in range(1, self.max_depth + 1):
            # перша ітерація завжди завершується; далі діє обмеження за часом
            self.deadline = (
                start + self.time_limit if self.time_limit and depth > 1 else None
            )
            try:
                scored, found, best_score = self._search_root(
                    game, cells, color, ordered, depth
                )
            except SearchTimeout:
                break
            self.reached_depth = depth
            best_moves = found
            # найкращі ходи — першими в наступній ітерації
            scored.sort(key=lambda item: item[0], reverse=True)
            ordered = [m for _, m in scored]
            if (
                abs(best_score) >= self.WIN_SCORE - 1000
            ):  # знайдено примусовий виграш/програш
                break

        chosen = random.choice(best_moves) if self.randomize_ties else best_moves[0]
        return self.pair_to_move(chosen)

    def _search_root(
        self,
        game: Game,
        cells: list[int],
        color: int,
        moves: list[tuple[int, int]],
        depth: int,
    ):
        opp = 3 - color
        scored: list[tuple[int, tuple[int, int]]] = []
        best_moves: list[tuple[int, int]] = []
        best = -INF
        for pair in moves:
            a, b = pair
            cells[b] = color
            cells[a] = 0
            if self.is_win(cells, color, b):
                score = self.WIN_SCORE  # виграш одразу
            elif game.position_counts.get(self.cells_to_key(cells, opp), 0) >= 2:
                score = 0  # третє повторення = нічия
            else:
                # вікно (best-1, +inf) дозволяє точно виявляти рівні ходи
                alpha = best - 1 if self.randomize_ties else best
                score = -self._negamax(cells, opp, depth - 1, -INF, -alpha, 1)
            cells[a] = color
            cells[b] = 0

            scored.append((score, pair))
            if score > best:
                best, best_moves = score, [pair]
            elif self.randomize_ties and score == best:
                best_moves.append(pair)
            if score >= self.WIN_SCORE:
                break
        return scored, best_moves, best

    # ------------------------------------------------------------------
    def alpha_beta(
        self,
        cells: list[int],
        color: int,
        depth: int,
        alpha: int,
        beta: int,
        ply: int = 0,
    ) -> int:
        """Публічна назва алгоритму (див. _negamax)."""
        return self._negamax(cells, color, depth, alpha, beta, ply)

    def _negamax(
        self, cells: list[int], color: int, depth: int, alpha: int, beta: int, ply: int
    ) -> int:
        self.nodes += 1
        if (
            self.deadline is not None
            and (self.nodes & 511) == 0
            and time.perf_counter() > self.deadline
        ):
            raise SearchTimeout

        moves = self.generate_moves(cells, color)
        if not moves:
            return -self.WIN_SCORE + ply  # немає ходів — програш

        # 1) якщо є виграш в один хід — далі шукати не потрібно
        for a, b in moves:
            cells[b] = color
            cells[a] = 0
            won = self.is_win(cells, color, b)
            cells[a] = color
            cells[b] = 0
            if won:
                return self.WIN_SCORE - ply

        # 2) межа глибини — евристична оцінка
        if depth <= 0:
            return self.evaluate(cells, color)

        # 3) таблиця транспозицій
        alpha0, beta0 = alpha, beta
        key = None
        tt_move = None
        if self.use_transposition:
            key = (bytes(cells), color)
            entry = self.transposition_table.get(key)
            if entry is not None:
                e_depth, flag, e_score, e_move = entry
                tt_move = e_move
                if e_depth >= depth:
                    if flag == _EXACT:
                        return e_score
                    if flag == _LOWER:
                        alpha = max(alpha, e_score)
                    else:
                        beta = min(beta, e_score)
                    if alpha >= beta:
                        return e_score

        if depth >= 2:
            moves = self.order_moves(cells, moves, color, tt_move)

        # 4) основний цикл з відсіканням
        opp = 3 - color
        best = -INF
        best_move = None
        for pair in moves:
            a, b = pair
            cells[b] = color
            cells[a] = 0
            score = -self._negamax(cells, opp, depth - 1, -beta, -alpha, ply + 1)
            cells[a] = color
            cells[b] = 0
            if score > best:
                best, best_move = score, pair
            if best > alpha:
                alpha = best
            if alpha >= beta:  # відсікання
                break

        if key is not None:
            flag = _EXACT
            if best <= alpha0:
                flag = _UPPER
            elif best >= beta0:
                flag = _LOWER
            if len(self.transposition_table) > 400_000:
                self.transposition_table.clear()
            self.transposition_table[key] = (depth, flag, best, best_move)
        return best

    def order_moves(
        self,
        cells: list[int],
        moves: list[tuple[int, int]],
        color: int,
        tt_move: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        """Спершу — хід із таблиці, потім ходи, що блокують двійки суперника
        або підсилюють власні лінії."""
        opp = 3 - color
        scored = []
        for pair in moves:
            a, b = pair
            s = 1_000_000 if pair == tt_move else 0
            for w in WINDOWS_BY_CELL[b]:
                own = his = 0
                for c in w:
                    if c == a:
                        continue
                    v = cells[c]
                    if v == color:
                        own += 1
                    elif v == opp:
                        his += 1
                if his == 2:
                    s += 20  # блокуємо майже готову лінію
                elif his == 0:
                    s += own * own
            scored.append((s, pair))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [pair for _, pair in scored]


class EasyStrategy(AlphaBetaStrategy):
    """Легкий: «жадібний» ШІ. Дивиться лише на один хід уперед: забирає
    миттєву перемогу, уникає ходу, після якого суперник виграє одразу,
    інакше вибирає хід із найкращою оцінкою позиції. Не випадковий."""

    def __init__(self, color: PlayerColor) -> None:
        super().__init__(color, max_depth=1, randomize_ties=True)


class MediumStrategy(AlphaBetaStrategy):
    """Середній: альфа-бета відсікання на малу глибину (без обмеження часу)."""

    def __init__(self, color: PlayerColor, depth: int = 3) -> None:
        super().__init__(color, max_depth=depth, randomize_ties=True)
        self.depth: int = depth


class HardStrategy(AlphaBetaStrategy):
    """Складний: альфа-бета з ітеративним поглибленням, таблицею транспозицій,
    впорядкуванням ходів та обмеженням часу на хід."""

    def __init__(
        self, color: PlayerColor, depth: int = 10, time_limit: float = 4.0
    ) -> None:
        super().__init__(
            color,
            max_depth=depth,
            time_limit=time_limit,
            use_transposition=True,
            randomize_ties=False,
        )
        self.depth: int = depth


class AIStrategyFactory:
    """Створює стратегію за рівнем складності."""

    @staticmethod
    def create(difficulty: Difficulty, color: PlayerColor) -> AIStrategy:
        if difficulty == Difficulty.EASY:
            return EasyStrategy(color)
        if difficulty == Difficulty.MEDIUM:
            return MediumStrategy(color)
        return HardStrategy(color)


# ======================================================================
# Гравці
# ======================================================================


class Player(ABC):
    """Базовий клас гравця."""

    def __init__(self, color: PlayerColor, name: str) -> None:
        self.color: PlayerColor = color
        self.name: str = name

    @abstractmethod
    def is_human(self) -> bool:
        pass


class HumanPlayer(Player):
    """Людина — ходи надходять із GUI."""

    def is_human(self) -> bool:
        return True


class AIPlayer(Player):
    """Комп'ютер — хід обирає стратегія."""

    def __init__(self, color: PlayerColor, difficulty: Difficulty) -> None:
        super().__init__(color, f"Комп'ютер: {DIFFICULTY_NAMES[difficulty]}")
        self.difficulty: Difficulty = difficulty
        self.strategy: AIStrategy = AIStrategyFactory.create(difficulty, color)

    def is_human(self) -> bool:
        return False

    def get_move(self, game: Game) -> Move:
        """Запитує хід у стратегії."""
        return self.strategy.choose_move(game)


# ======================================================================
# Контролер
# ======================================================================


class GameController:
    """Зв'язує модель (Game), гравців та інтерфейс (View)."""

    def __init__(self, view: "MainWindow") -> None:
        self.view: "MainWindow" = view
        self.game: Optional[Game] = None
        self.players: dict[PlayerColor, Player] = {}
        self.difficulty: Difficulty = Difficulty.EASY
        self.selected_position: Optional[Position] = None
        self.ai_thinking: bool = False
        self.ai_min_delay: float = 0.4  # мінімальна «пауза на роздуми», с

    def start_new_game(
        self,
        mode: GameMode,
        difficulty: Difficulty,
        human_color: PlayerColor = PlayerColor.BLACK,
    ) -> None:
        """Створює гравців і нову партію."""
        self.difficulty = difficulty
        self.selected_position = None
        self.ai_thinking = False

        if mode == GameMode.HUMAN_VS_AI:
            ai_color = (
                PlayerColor.WHITE
                if human_color == PlayerColor.BLACK
                else PlayerColor.BLACK
            )
            self.players = {
                human_color: HumanPlayer(human_color, "Ви"),
                ai_color: AIPlayer(ai_color, difficulty),
            }
        else:
            self.players = {
                PlayerColor.BLACK: HumanPlayer(PlayerColor.BLACK, "Гравець 1"),
                PlayerColor.WHITE: HumanPlayer(PlayerColor.WHITE, "Гравець 2"),
            }

        self.game = Game(mode)
        self.game.new_game()
        self.view.show_game()
        self.view.refresh_board(self.game)
        self.request_ai_move()  # якщо першим ходить комп'ютер

    def on_cell_clicked(self, pos: Position) -> None:
        """Обробка кліку: вибір фішки або виконання ходу."""
        game = self.game
        if game is None or game.is_over():
            return
        if not self.players[game.current_color].is_human():
            return  # зараз хід комп'ютера
        if game.board.get(pos) == game.current_color:
            if self.selected_position == pos:  # повторний клік — скасувати вибір
                self.deselect()
            else:
                self.select_piece(pos)
        elif self.selected_position is not None:
            self.try_move(Move(self.selected_position, pos))

    def select_piece(self, pos: Position) -> None:
        """Вибір фішки та підсвічування можливих ходів."""
        canvas = self.view.game_frame.board_canvas
        self.selected_position = pos
        canvas.highlight_selected(pos)
        moves = Rules.get_legal_moves_for_piece(self.game.board, pos)
        canvas.highlight_cells([m.end for m in moves])

    def deselect(self) -> None:
        """Знімає вибір фішки та підсвічування."""
        canvas = self.view.game_frame.board_canvas
        self.selected_position = None
        canvas.highlight_selected(None)
        canvas.highlight_cells([])

    def try_move(self, move: Move) -> None:
        """Спроба виконати хід людини."""
        if self.game.make_move(move):
            self.selected_position = None
            self.finish_turn()
        else:
            self.deselect()  # клік не по допустимій клітинці

    def request_ai_move(self) -> None:
        """Запускає хід комп'ютера (бажано з невеликою затримкою, after())."""
        game = self.game
        if game is None or game.is_over() or self.ai_thinking:
            return
        player = self.players[game.current_color]
        if player.is_human():
            return

        self.ai_thinking = True
        self.view.game_frame.update_status("Комп'ютер думає…")
        snapshot = game.copy()
        result: dict = {}

        def worker() -> None:
            try:
                result["move"] = player.get_move(snapshot)
            except Exception as error:  # помилка ШІ не повинна «вішати» гру
                result["error"] = error

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self._poll_ai_move(game, thread, result, time.monotonic())

    def _poll_ai_move(
        self, game: Game, thread: threading.Thread, result: dict, started: float
    ) -> None:
        """Чекає на хід ШІ, не блокуючи інтерфейс; виконує його в головному потоці."""
        if self.game is not game:  # користувач почав нову партію
            return
        if self.view.game_frame is None:  # користувач вийшов у меню
            self.ai_thinking = False
            return
        if thread.is_alive() or time.monotonic() - started < self.ai_min_delay:
            self.view.after(
                50, lambda: self._poll_ai_move(game, thread, result, started)
            )
            return
        self.ai_thinking = False
        move = result.get("move")
        if move is None:
            self.view.show_message(
                "Помилка", f"ШІ не зміг зробити хід: {result.get('error')}"
            )
            return
        self.try_move(move)

    def finish_turn(self) -> None:
        """Оновлює інтерфейс, перевіряє кінець гри, передає хід."""
        self.view.game_frame.board_canvas.clear_highlights()
        self.view.refresh_board(self.game)
        if self.game.is_over():
            self.on_game_over()
        else:
            self.request_ai_move()

    def on_game_over(self) -> None:
        """Показує результат гри."""
        game, frame = self.game, self.view.game_frame
        frame.board_canvas.highlight_winning_line(game.winning_line)
        frame.show_game_over(game.status)
        self.view.update_idletasks()  # намалювати лінію до появи вікна
        self.view.show_message("Кінець гри", RESULT_TEXTS[game.status])

    def restart(self) -> None:
        if self.game is None:
            return
        mode = self.game.mode
        human_color = next(
            (c for c, p in self.players.items() if p.is_human()), PlayerColor.BLACK
        )
        self.start_new_game(mode, self.difficulty, human_color)


# ======================================================================
# Графічний інтерфейс (tkinter)
# ======================================================================


class BoardCanvas(tk.Canvas):
    """Малює дошку, фішки, підсвічування (стиль: синє поле, зелені координати)."""

    # --- Кольори дизайну ---
    COLOR_BOARD = "#5571B5"  # синє поле
    COLOR_BORDER = "#4A63A6"  # трохи темніша рамка з координатами
    COLOR_LINES = "#0A0A14"  # чорні лінії сітки
    COLOR_LABEL = "#1FB01F"  # зелені координати
    COLOR_SELECTED = "#FFE066"  # рамка вибраної фішки
    COLOR_HINT = "#9BE37A"  # позначка можливого ходу

    # (зовнішній край, центр, колір відблиску)
    PIECE_STYLES = {
        PlayerColor.WHITE: ("#8C8C94", "#F4F4F8", "#FFFFFF"),
        PlayerColor.BLACK: ("#050505", "#4A4A50", "#9A9AA2"),
    }

    COLUMN_LABELS = "ABCDE"

    def __init__(
        self,
        master: tk.Widget,
        cell_size: int = 76,
        on_click: Optional[Callable[[Position], None]] = None,
    ) -> None:
        self.cell_size: int = cell_size
        self.margin: int = 22  # ширина рамки з координатами
        self.on_click: Optional[Callable[[Position], None]] = on_click
        self.selected: Optional[Position] = None
        self.highlighted: list[Position] = []
        self.winning_line: list[Position] = []

        total = BOARD_SIZE * cell_size + 2 * self.margin
        super().__init__(
            master,
            width=total,
            height=total,
            highlightthickness=0,
            bg=self.COLOR_BORDER,
        )
        self.bind("<Button-1>", self._handle_click)
        self.draw_board()

    # ------------------------------------------------------------------
    # Дошка
    # ------------------------------------------------------------------
    def draw_board(self) -> None:
        """Малює поле, рамку, сітку та координати A–E / 1–5."""
        self.delete("board")
        m, cs = self.margin, self.cell_size
        total = BOARD_SIZE * cs + 2 * m
        inner_end = m + BOARD_SIZE * cs

        # рамка (зовнішній і внутрішній контур) та синє поле
        self.create_rectangle(
            2,
            2,
            total - 2,
            total - 2,
            fill=self.COLOR_BORDER,
            outline=self.COLOR_LINES,
            width=2,
            tags="board",
        )
        self.create_rectangle(
            m,
            m,
            inner_end,
            inner_end,
            fill=self.COLOR_BOARD,
            outline=self.COLOR_LINES,
            width=2,
            tags="board",
        )

        # лінії сітки (включно з тими, що відокремлюють рамку з підписами)
        for i in range(BOARD_SIZE + 1):
            p = m + i * cs
            self.create_line(
                p, 2, p, total - 2, fill=self.COLOR_LINES, width=1, tags="board"
            )
            self.create_line(
                2, p, total - 2, p, fill=self.COLOR_LINES, width=1, tags="board"
            )

        # координати
        font = ("Verdana", 9, "bold")
        for i in range(BOARD_SIZE):
            c = m + i * cs + cs // 2
            letter, number = self.COLUMN_LABELS[i], str(i + 1)
            self.create_text(
                c,
                m // 2 + 1,
                text=letter,
                fill=self.COLOR_LABEL,
                font=font,
                tags="board",
            )
            self.create_text(
                c,
                total - m // 2,
                text=letter,
                fill=self.COLOR_LABEL,
                font=font,
                tags="board",
            )
            self.create_text(
                m // 2 + 1,
                c,
                text=number,
                fill=self.COLOR_LABEL,
                font=font,
                tags="board",
            )
            self.create_text(
                total - m // 2,
                c,
                text=number,
                fill=self.COLOR_LABEL,
                font=font,
                tags="board",
            )

    # ------------------------------------------------------------------
    # Фішки
    # ------------------------------------------------------------------
    @staticmethod
    def _blend(c1: str, c2: str, t: float) -> str:
        """Лінійне змішування двох HEX-кольорів (t=0 -> c1, t=1 -> c2)."""
        r1, g1, b1 = (int(c1[i : i + 2], 16) for i in (1, 3, 5))
        r2, g2, b2 = (int(c2[i : i + 2], 16) for i in (1, 3, 5))
        return "#{:02x}{:02x}{:02x}".format(
            round(r1 + (r2 - r1) * t),
            round(g1 + (g2 - g1) * t),
            round(b1 + (b2 - b1) * t),
        )

    def draw_piece(self, pos: Position, color: PlayerColor) -> None:
        """Малює одну об'ємну фішку (тінь + градієнт з кілець + відблиск)."""
        cx, cy = self.position_to_pixel(pos)
        r = int(self.cell_size * 0.34)
        edge, center, shine = self.PIECE_STYLES[color]

        # тінь
        self.create_oval(
            cx - r + 3,
            cy - r + 4,
            cx + r + 3,
            cy + r + 4,
            fill="#33447A",
            outline="",
            tags="piece",
        )

        # градієнт: концентричні кола від краю до центру
        steps = 7
        for i in range(steps):
            k = i / (steps - 1)
            rad = r * (1 - 0.62 * k)
            shift = -r * 0.10 * k  # центр трохи зміщений вгору-вліво
            self.create_oval(
                cx - rad + shift,
                cy - rad + shift,
                cx + rad + shift,
                cy + rad + shift,
                fill=self._blend(edge, center, k),
                outline=edge if i == 0 else "",
                width=1,
                tags="piece",
            )

        # відблиск
        hr = r * 0.22
        hx, hy = cx - r * 0.35, cy - r * 0.38
        self.create_oval(
            hx - hr,
            hy - hr * 0.7,
            hx + hr,
            hy + hr * 0.7,
            fill=self._blend(center, shine, 0.6),
            outline="",
            tags="piece",
        )

    def draw_pieces(self, board: Board) -> None:
        """Малює всі фішки з дошки."""
        self.delete("piece")
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                pos = Position(row, col)
                color = board.get(pos)
                if color is not None:
                    self.draw_piece(pos, color)

    # ------------------------------------------------------------------
    # Підсвічування
    # ------------------------------------------------------------------
    def _cell_rect(self, pos: Position, pad: int = 0) -> tuple[int, int, int, int]:
        x = self.margin + pos.col * self.cell_size
        y = self.margin + pos.row * self.cell_size
        return x + pad, y + pad, x + self.cell_size - pad, y + self.cell_size - pad

    def _lower_highlights(self) -> None:
        """Підсвічування має лежати під фішками, але над дошкою."""
        if self.find_withtag("piece"):
            self.tag_lower("highlight", "piece")

    def highlight_cells(self, positions: list[Position]) -> None:
        """Підсвічує можливі ходи (зелені точки)."""
        self.highlighted = list(positions)
        self.delete("hint")
        for pos in positions:
            x1, y1, x2, y2 = self._cell_rect(pos)
            cx, cy, r = (x1 + x2) / 2, (y1 + y2) / 2, self.cell_size * 0.11
            self.create_oval(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                fill=self.COLOR_HINT,
                outline=self.COLOR_LINES,
                tags=("highlight", "hint"),
            )
        self._lower_highlights()

    def highlight_selected(self, pos: Optional[Position]) -> None:
        """Жовта рамка навколо вибраної фішки."""
        self.selected = pos
        self.delete("selected")
        if pos is None:
            return
        x1, y1, x2, y2 = self._cell_rect(pos, pad=3)
        self.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline=self.COLOR_SELECTED,
            width=3,
            tags=("highlight", "selected"),
        )
        self._lower_highlights()

    def highlight_winning_line(self, positions: list[Position]) -> None:
        """Лінія через три фішки-переможці."""
        self.winning_line = list(positions)
        self.delete("winline")
        if len(positions) < 2:
            return
        p1 = self.position_to_pixel(positions[0])
        p2 = self.position_to_pixel(positions[-1])
        self.create_line(
            *p1, *p2, fill="#FF4040", width=5, capstyle="round", tags="winline"
        )

    def clear_highlights(self) -> None:
        self.selected = None
        self.highlighted = []
        self.winning_line = []
        self.delete("highlight", "winline")

    # ------------------------------------------------------------------
    # Анімація, координати, події
    # ------------------------------------------------------------------
    def animate_move(self, move: Move, color: PlayerColor) -> None:
        """Анімація ковзання фішки (опційно, поки не реалізовано)."""
        pass

    def pixel_to_position(self, x: int, y: int) -> Optional[Position]:
        """Піксельні координати -> клітинка (None, якщо клік поза полем)."""
        col = (x - self.margin) // self.cell_size
        row = (y - self.margin) // self.cell_size
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return Position(row, col)
        return None

    def position_to_pixel(self, pos: Position) -> tuple[int, int]:
        """Клітинка -> піксельні координати її центру."""
        x = self.margin + pos.col * self.cell_size + self.cell_size // 2
        y = self.margin + pos.row * self.cell_size + self.cell_size // 2
        return x, y

    def _handle_click(self, event: tk.Event) -> None:
        pos = self.pixel_to_position(event.x, event.y)
        if pos is not None and self.on_click is not None:
            self.on_click(pos)

    def refresh(self, game: Game) -> None:
        """Повне перемальовування за станом гри."""
        self.draw_board()
        self.draw_pieces(game.board)
        self.highlight_selected(self.selected)
        self.highlight_cells(self.highlighted)
        self.highlight_winning_line(self.winning_line)


UI_BG = "#2E3F73"
UI_FG = "#FFFFFF"
UI_ACCENT = "#5571B5"
UI_FONT = ("Verdana", 11)
UI_FONT_BOLD = ("Verdana", 11, "bold")


def make_button(
    master: tk.Widget, text: str, command: Callable[[], None], width: int = 18
) -> tk.Button:
    """Єдиний стиль кнопок."""
    return tk.Button(
        master,
        text=text,
        command=command,
        width=width,
        font=UI_FONT_BOLD,
        bg=UI_ACCENT,
        fg=UI_FG,
        activebackground="#6B88D0",
        activeforeground=UI_FG,
        relief="flat",
        bd=0,
        pady=6,
        cursor="hand2",
    )


class MenuFrame(tk.Frame):
    """Головне меню: режим, складність, колір, старт."""

    def __init__(
        self,
        master: tk.Widget,
        on_start: Callable[[GameMode, Difficulty, PlayerColor], None],
    ) -> None:
        super().__init__(master, bg=UI_BG, padx=50, pady=30)
        self.on_start = on_start
        self.difficulty_var: tk.IntVar = tk.IntVar(value=Difficulty.EASY.value)
        self.mode_var: tk.IntVar = tk.IntVar(value=GameMode.HUMAN_VS_AI.value)
        self.color_var: tk.IntVar = tk.IntVar(value=PlayerColor.BLACK.value)
        self.ai_only_widgets: list[tk.Widget] = []
        self.build_widgets()

    def _section(
        self,
        title: str,
        var: tk.IntVar,
        options: list[tuple[str, int]],
        ai_only: bool = False,
    ) -> None:
        tk.Label(self, text=title, font=UI_FONT_BOLD, bg=UI_BG, fg="#9BE37A").pack(
            anchor="w", pady=(14, 2)
        )
        for text, value in options:
            rb = tk.Radiobutton(
                self,
                text=text,
                variable=var,
                value=value,
                font=UI_FONT,
                bg=UI_BG,
                fg=UI_FG,
                selectcolor=UI_BG,
                activebackground=UI_BG,
                activeforeground=UI_FG,
                disabledforeground="#7C88AD",
                command=self._update_states,
            )
            rb.pack(anchor="w")
            if ai_only:
                self.ai_only_widgets.append(rb)

    def build_widgets(self) -> None:
        tk.Label(
            self, text="НЕЙТРІКО", font=("Verdana", 26, "bold"), bg=UI_BG, fg=UI_FG
        ).pack(pady=(0, 6))
        tk.Label(
            self, text="Збери три фішки в ряд", font=UI_FONT, bg=UI_BG, fg="#C7D2F0"
        ).pack()

        self._section(
            "Режим гри",
            self.mode_var,
            [
                ("Гравець проти комп'ютера", GameMode.HUMAN_VS_AI.value),
                ("Двоє гравців", GameMode.HUMAN_VS_HUMAN.value),
            ],
        )
        self._section(
            "Складність",
            self.difficulty_var,
            [(DIFFICULTY_NAMES[d], d.value) for d in Difficulty],
            ai_only=True,
        )
        self._section(
            "Ваш колір (чорні ходять першими)",
            self.color_var,
            [(COLOR_NAMES[c], c.value) for c in PlayerColor],
            ai_only=True,
        )

        make_button(self, "Грати", self._start_clicked).pack(pady=(24, 6))
        make_button(self, "Вийти", self.winfo_toplevel().destroy).pack()
        self._update_states()

    def _update_states(self) -> None:
        """Складність і колір доступні лише у грі проти комп'ютера."""
        vs_ai = self.mode_var.get() == GameMode.HUMAN_VS_AI.value
        for w in self.ai_only_widgets:
            w.configure(state="normal" if vs_ai else "disabled")

    def _start_clicked(self) -> None:
        self.on_start(
            GameMode(self.mode_var.get()),
            Difficulty(self.difficulty_var.get()),
            PlayerColor(self.color_var.get()),
        )


class GameFrame(tk.Frame):
    """Екран гри: дошка + панель інформації + кнопки."""

    def __init__(self, master: tk.Widget, controller: GameController) -> None:
        super().__init__(master, bg=UI_BG, padx=20, pady=15)
        self.controller: GameController = controller
        self.board_canvas: Optional[BoardCanvas] = None
        self.status_label: Optional[tk.Label] = None
        self.turn_label: Optional[tk.Label] = None
        self.build_widgets()

    def build_widgets(self) -> None:
        self.turn_label = tk.Label(
            self, text="", font=("Verdana", 14, "bold"), bg=UI_BG, fg=UI_FG
        )
        self.turn_label.pack(pady=(0, 10))

        self.board_canvas = BoardCanvas(self, on_click=self.controller.on_cell_clicked)
        self.board_canvas.pack()

        self.status_label = tk.Label(
            self, text="", font=UI_FONT, bg=UI_BG, fg="#C7D2F0"
        )
        self.status_label.pack(pady=10)

        buttons = tk.Frame(self, bg=UI_BG)
        buttons.pack()
        make_button(buttons, "Нова гра", self.controller.restart, width=14).pack(
            side="left", padx=6
        )
        make_button(buttons, "У меню", self.master.show_menu, width=14).pack(
            side="left", padx=6
        )

    def update_turn(self, player: Player) -> None:
        self.turn_label.config(text=f"Хід: {COLOR_NAMES[player.color]} ({player.name})")

    def update_status(self, text: str) -> None:
        self.status_label.config(text=text)

    def show_game_over(self, status: GameStatus) -> None:
        self.update_status(RESULT_TEXTS.get(status, ""))


class MainWindow(tk.Tk):
    """Головне вікно застосунку; перемикає екрани."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Нейтріко")
        self.configure(bg=UI_BG)
        self.resizable(False, False)
        self.controller: GameController = GameController(self)
        self.menu_frame: Optional[MenuFrame] = None
        self.game_frame: Optional[GameFrame] = None

    def _clear(self) -> None:
        """Прибирає поточний екран."""
        for frame in (self.menu_frame, self.game_frame):
            if frame is not None:
                frame.destroy()
        self.menu_frame = None
        self.game_frame = None

    def _center(self) -> None:
        """Центрує вікно на екрані."""
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def show_menu(self) -> None:
        self._clear()
        self.menu_frame = MenuFrame(self, on_start=self.controller.start_new_game)
        self.menu_frame.pack()
        self._center()

    def show_game(self) -> None:
        self._clear()
        self.game_frame = GameFrame(self, self.controller)
        self.game_frame.pack()
        self._center()

    def refresh_board(self, game: Game) -> None:
        if self.game_frame is None:
            return
        self.game_frame.board_canvas.refresh(game)
        if game.is_over():
            self.game_frame.turn_label.config(text="Гру завершено")
        else:
            self.game_frame.update_turn(self.controller.players[game.current_color])
        self.game_frame.update_status("")

    def show_message(self, title: str, text: str) -> None:
        messagebox.showinfo(title, text)


# ======================================================================
# Точка входу
# ======================================================================


def main() -> None:
    app = MainWindow()
    app.show_menu()
    app.mainloop()


if __name__ == "__main__":
    main()
