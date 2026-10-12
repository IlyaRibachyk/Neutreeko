"""
Нейтріко (Neutreeko) — структура гри (версія 1, каркас).
Лише класи, властивості та методи; логіка не реалізована.

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
        pass

    def shifted(self, d_row: int, d_col: int) -> Position:
        """Повертає нову позицію зі зсувом."""
        pass


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

    def reset(self) -> None:
        """Розставляє фішки у початкову позицію."""
        pass

    def get(self, pos: Position) -> Optional[PlayerColor]:
        """Повертає колір фішки в клітинці або None, якщо вона порожня."""
        pass

    def is_empty(self, pos: Position) -> bool:
        """Чи порожня клітинка."""
        pass

    def get_pieces(self, color: PlayerColor) -> list[Piece]:
        """Усі фішки гравця."""
        pass

    def apply_move(self, move: Move) -> None:
        """Виконує хід на дошці."""
        pass

    def undo_move(self, move: Move) -> None:
        """Скасовує хід (потрібно для пошуку ШІ)."""
        pass

    def copy(self) -> Board:
        """Глибока копія дошки."""
        pass

    def to_key(self) -> tuple:
        """Незмінне представлення позиції (для підрахунку повторів)."""
        pass


class Rules:
    """Правила гри (без стану)."""

    @staticmethod
    def slide_destination(
        board: Board, start: Position, direction: tuple[int, int]
    ) -> Optional[Position]:
        """Куди зупиниться фішка, ковзаючи у напрямку; None, якщо рухатись не можна."""
        pass

    @staticmethod
    def get_legal_moves_for_piece(board: Board, position: Position) -> list[Move]:
        """Усі допустимі ходи однієї фішки."""
        pass

    @staticmethod
    def get_legal_moves(board: Board, color: PlayerColor) -> list[Move]:
        """Усі допустимі ходи гравця."""
        pass

    @staticmethod
    def is_legal_move(board: Board, move: Move, color: PlayerColor) -> bool:
        """Перевірка допустимості ходу."""
        pass

    @staticmethod
    def has_three_in_row(board: Board, color: PlayerColor) -> bool:
        """Чи є в гравця три фішки в ряд."""
        pass

    @staticmethod
    def find_three_in_row(board: Board, color: PlayerColor) -> list[Position]:
        """Повертає три клітинки виграшної лінії або порожній список."""
        pass


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
        pass

    def make_move(self, move: Move) -> bool:
        """Виконує хід, оновлює чергу, історію й статус. False, якщо хід недопустимий."""
        pass

    def switch_turn(self) -> None:
        """Передає хід іншому гравцю."""
        pass

    def update_status(self) -> None:
        """Перевіряє перемогу / нічию."""
        pass

    def is_draw_by_repetition(self) -> bool:
        """Нічия за триразовим повторенням позиції."""
        pass

    def get_legal_moves(self) -> list[Move]:
        """Допустимі ходи поточного гравця."""
        pass

    def is_over(self) -> bool:
        """Чи закінчилась гра."""
        pass

    def copy(self) -> Game:
        """Незалежна копія партії (для ШІ)."""
        pass

    def undo_last_move(self) -> None:
        """Скасувати останній хід (опційно)."""
        pass


# ======================================================================
# Штучний інтелект (3 рівні складності)
# ======================================================================


class AIStrategy(ABC):
    """Базова стратегія ШІ."""

    def __init__(self, color: PlayerColor) -> None:
        self.color: PlayerColor = color

    @abstractmethod
    def choose_move(self, game: Game) -> Move:
        """Обирає хід для поточної позиції."""
        pass

    def evaluate(self, board: Board, color: PlayerColor) -> int:
        """Евристична оцінка позиції з погляду гравця."""
        pass


class EasyStrategy(AIStrategy):
    """Легкий: випадковий допустимий хід."""

    def choose_move(self, game: Game) -> Move:
        pass


class MediumStrategy(AIStrategy):
    """Середній: minimax на малу глибину."""

    def __init__(self, color: PlayerColor, depth: int = 3) -> None:
        super().__init__(color)
        self.depth: int = depth

    def choose_move(self, game: Game) -> Move:
        pass

    def minimax(self, game: Game, depth: int, maximizing: bool) -> int:
        """Рекурсивний пошук minimax."""
        pass


class HardStrategy(AIStrategy):
    """Складний: alpha-beta відсікання на більшу глибину."""

    def __init__(self, color: PlayerColor, depth: int = 6) -> None:
        super().__init__(color)
        self.depth: int = depth

    def choose_move(self, game: Game) -> Move:
        pass

    def alpha_beta(
        self, game: Game, depth: int, alpha: int, beta: int, maximizing: bool
    ) -> int:
        """Рекурсивний пошук з альфа-бета відсіканням."""
        pass


class AIStrategyFactory:
    """Створює стратегію за рівнем складності."""

    @staticmethod
    def create(difficulty: Difficulty, color: PlayerColor) -> AIStrategy:
        pass


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
        pass


class AIPlayer(Player):
    """Комп'ютер — хід обирає стратегія."""

    def __init__(self, color: PlayerColor, difficulty: Difficulty) -> None:
        super().__init__(color, "Комп'ютер")
        self.difficulty: Difficulty = difficulty
        self.strategy: Optional[AIStrategy] = None

    def is_human(self) -> bool:
        pass

    def get_move(self, game: Game) -> Move:
        """Запитує хід у стратегії."""
        pass


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

    def start_new_game(
        self,
        mode: GameMode,
        difficulty: Difficulty,
        human_color: PlayerColor = PlayerColor.BLACK,
    ) -> None:
        """Створює гравців і нову партію."""
        pass

    def on_cell_clicked(self, pos: Position) -> None:
        """Обробка кліку: вибір фішки або виконання ходу."""
        pass

    def select_piece(self, pos: Position) -> None:
        """Вибір фішки та підсвічування можливих ходів."""
        pass

    def deselect(self) -> None:
        """Знімає вибір фішки."""
        pass

    def try_move(self, move: Move) -> None:
        """Спроба виконати хід."""
        pass

    def request_ai_move(self) -> None:
        """Запускає хід комп'ютера."""
        pass

    def finish_turn(self) -> None:
        """Оновлює інтерфейс, перевіряє кінець гри, передає хід."""
        pass

    def on_game_over(self) -> None:
        """Показує результат гри."""
        pass

    def restart(self) -> None:
        """Нова партія з поточними налаштуваннями."""
        pass


# ======================================================================
# Графічний інтерфейс (tkinter)
# ======================================================================


class BoardCanvas(tk.Canvas):
    """Малює дошку, фішки, підсвічування."""

    def __init__(
        self,
        master: tk.Widget,
        cell_size: int = 76,
        on_click: Optional[Callable[[Position], None]] = None,
    ) -> None:
        super().__init__(master)
        self.cell_size: int = cell_size
        self.on_click: Optional[Callable[[Position], None]] = on_click
        self.selected: Optional[Position] = None
        self.highlighted: list[Position] = []

    def draw_board(self) -> None:
        """Малює поле та сітку."""
        pass

    def draw_piece(self, pos: Position, color: PlayerColor) -> None:
        """Малює одну фішку."""
        pass

    def draw_pieces(self, board: Board) -> None:
        """Малює всі фішки з дошки."""
        pass

    def highlight_selected(self, pos: Optional[Position]) -> None:
        """Підсвічує вибрану фішку."""
        pass

    def highlight_cells(self, positions: list[Position]) -> None:
        """Підсвічує можливі ходи."""
        pass

    def highlight_winning_line(self, positions: list[Position]) -> None:
        """Підсвічує виграшну лінію."""
        pass

    def clear_highlights(self) -> None:
        """Прибирає підсвічування."""
        pass

    def animate_move(self, move: Move, color: PlayerColor) -> None:
        """Анімація ковзання фішки (опційно)."""
        pass

    def pixel_to_position(self, x: int, y: int) -> Optional[Position]:
        """Піксельні координати -> клітинка."""
        pass

    def position_to_pixel(self, pos: Position) -> tuple[int, int]:
        """Клітинка -> піксельні координати її центру."""
        pass

    def refresh(self, game: Game) -> None:
        """Повне перемальовування за станом гри."""
        pass


class MenuFrame(tk.Frame):
    """Головне меню: режим, складність, колір, старт."""

    def __init__(
        self,
        master: tk.Widget,
        on_start: Callable[[GameMode, Difficulty, PlayerColor], None],
    ) -> None:
        super().__init__(master)
        self.on_start = on_start
        self.difficulty_var: Optional[tk.IntVar] = None
        self.mode_var: Optional[tk.IntVar] = None
        self.color_var: Optional[tk.IntVar] = None

    def build_widgets(self) -> None:
        """Створює елементи меню."""
        pass


class GameFrame(tk.Frame):
    """Екран гри: дошка + панель інформації + кнопки."""

    def __init__(self, master: tk.Widget, controller: GameController) -> None:
        super().__init__(master)
        self.controller: GameController = controller
        self.board_canvas: Optional[BoardCanvas] = None
        self.status_label: Optional[tk.Label] = None
        self.turn_label: Optional[tk.Label] = None

    def build_widgets(self) -> None:
        """Створює елементи екрана гри."""
        pass

    def update_turn(self, player: Player) -> None:
        """Показує, чий зараз хід."""
        pass

    def update_status(self, text: str) -> None:
        """Оновлює рядок стану."""
        pass

    def show_game_over(self, status: GameStatus) -> None:
        """Показує результат гри."""
        pass


class MainWindow(tk.Tk):
    """Головне вікно застосунку; перемикає екрани."""

    def __init__(self) -> None:
        super().__init__()
        self.controller: GameController = GameController(self)
        self.menu_frame: Optional[MenuFrame] = None
        self.game_frame: Optional[GameFrame] = None

    def show_menu(self) -> None:
        """Показує головне меню."""
        pass

    def show_game(self) -> None:
        """Показує екран гри."""
        pass

    def refresh_board(self, game: Game) -> None:
        """Оновлює відображення дошки."""
        pass

    def show_message(self, title: str, text: str) -> None:
        """Показує діалогове повідомлення."""
        pass


# ======================================================================
# Точка входу
# ======================================================================


def main() -> None:
    app = MainWindow()
    app.show_menu()
    app.mainloop()


if __name__ == "__main__":
    main()
