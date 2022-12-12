import random
from collections import defaultdict
from copy import deepcopy
from csv import DictReader, excel_tab
from enum import Enum
from typing import Iterable, Optional, NamedTuple

from word_search_generator.utils import get_random_words  # for development testing


class CellOccupiedError(Exception):
    pass


class Position(NamedTuple):
    row: int
    col: int

    def __add__(self, other: "Position | int"):
        return (
            Position(self.row + other.row, self.col + other.col)
            if isinstance(other, Position)
            else Position(self.row + other, self.col + other)
        )

    def __mul__(self, other: int):
        return Position(self.row * other, self.col * other)

    def __sub__(self, other: "int | Position"):
        return (
            Position(self.row - other, self.col - other)
            if isinstance(other, int)
            else Position(self.row - other.row, self.col - other.col)
        )


class Direction(Enum):
    ACROSS = Position(0, 1)
    DOWN = Position(1, 0)

    def next(self, p: Position) -> Position:
        return p + self.value

    def __mul__(self, other: int):
        return Position(self.value.row * other, self.value.col * other)


class Bearing(NamedTuple):
    position: Position
    direction: Direction


class Word:
    def __init__(self, text: str, hint: str, mandatory: bool = True):
        self.word: str = text.upper().strip()
        if len(self.word) < 2:
            raise ValueError(f"{self.word} is too short of a word")
        self.hint: str = hint.strip()
        self.start: Optional[Bearing] = None
        self.required: bool = mandatory
        self.number: int = 0

    def __len__(self):
        return len(self.word)

    def __bool__(self):
        return self.start is not None

    def __eq__(self, other):
        return self.word == other.word


class Cell:
    def __init__(self, letter: str = "", **kwargs):
        self.letter = letter.upper().strip()
        self.word_across: bool = False
        self.word_down: bool = False
        self.on_boundary: bool = kwargs.get("boundary")
        self.is_valid: bool = not kwargs.get("invalid")
        self.number: int = 0

    @property
    def available(self):
        return self.is_valid and not (self.word_down and self.word_across)

    def display(self, show_solution: bool) -> str:
        if self.number:
            return f"{self.number} "
        if not show_solution:
            return f"[]"
        if self.letter:
            return f"{self.letter} "
        return "  "


OOB_CELL = Cell(boundary=True, invalid=True)
Cells = dict[Position, Cell]


class Crossword:
    def __init__(self, words: Iterable[Word]):
        self.word_list: list[Word] = []
        self.cells: Cells = {}
        for word in words:
            # break this into a function
            self.word_list.append(word)
            # find candidate cells
            # validate the cells
            candidates = []
            for candidate in self.find_candidate_intersections(word):
                try:
                    place_a_word(self.cells, word, candidate, False)
                    candidates.append(candidate)
                except CellOccupiedError:
                    continue
            if not candidates:
                candidates = [self.pick_random_empty_cell()]
                # print(f"Not an intersection yet\n{self.cells}\n{candidates}")

            # pick one
            place_a_word(self.cells, word, random.choice(candidates), True)
        # assign numbers
        current_number, current_position = 0, Position(-1, -1)
        for word in sorted(self.word_list, key=lambda w: w.start):
            if word.start is None:
                continue
            if current_position != word.start.position:
                current_number += 1
            word.number = current_number
            self.cells[word.start.position].number = current_number

    def find_candidate_intersections(self, w: Word) -> list[Bearing]:
        options: list[Bearing] = []
        for offset, letter in enumerate(w.word):
            for candidate in self.letter_list[letter]:
                options.append(
                    Bearing(
                        candidate.position - candidate.direction * offset,
                        candidate.direction,
                    )
                )
        return options

    def pick_random_empty_cell(self) -> Bearing:
        if not self.cells:
            return Bearing(
                Position(7, 7), random.choice([Direction.DOWN, Direction.ACROSS])
            )

    @property
    def required_words(self) -> set[Word]:
        return {w for w in self.word_list if w.required}

    @property
    def optional_words(self) -> set[Word]:
        return {w for w in self.word_list if not w.required}

    @property
    def placed_words(self) -> set[Word]:
        return {w for w in self.word_list if w}

    @property
    def unplaced_words(self) -> set[Word]:
        return {w for w in self.word_list if not w}

    @property
    def missing_mandatory_words(self) -> set[Word]:
        return self.unplaced_words & self.required_words

    @property
    def letter_list(self) -> dict[str, set[Bearing]]:
        d = defaultdict(set)
        for coords, content in self.cells.items():
            if not content.is_valid or not content.available:
                continue
            if not content.word_down:
                d[content.letter].add(Bearing(coords, Direction.DOWN))
            if not content.word_across:
                d[content.letter].add(Bearing(coords, Direction.ACROSS))
        return d

    @property
    def histogram(self) -> tuple[list[int], list[int]]:
        rows: list[int] = []
        cols: list[int] = []
        for c in self.cells.keys():
            rows.append(c.row)
            cols.append(c.col)
        return sorted(rows), sorted(cols)

    @property
    def extrema(self) -> tuple[Position, Position]:
        r, c = self.histogram
        return Position(r[0], c[0]), Position(r[-1], c[-1])

    @property
    def words_across(self) -> list[Word]:
        return [w for w in self.word_list if w.start.direction == Direction.ACROSS]

    @property
    def words_down(self) -> list[Word]:
        return [w for w in self.word_list if w.start.direction == Direction.DOWN]

    def recenter(self):
        offset, _ = self.extrema
        if offset == Position(0, 0):
            return  # nothing to do
        self.cells = {position - offset: cell for position, cell in self.cells.items()}
        for word in self.word_list:
            word.start = Bearing(word.start.position - offset, word.start.direction)

    def solution_only(self) -> list[list[str]]:
        self.recenter()
        size = self.extrema[1] + 1
        out = [["  "] * size.col for _ in range(size.row)]
        for p, c in self.cells.items():
            out[p.row][p.col] = c.display(True)
        return out

    def terminal_display(self) -> list[list[str]]:
        self.recenter()
        size = self.extrema[1] + 1
        out = [["<>"] * size.col for _ in range(size.row)]
        for p, c in self.cells.items():
            out[p.row][p.col] = c.display(False)
        return out

    def hint_list(self, d: Direction) -> list[str]:
        return [
            f"{w.number}. {w.hint}"
            for w in sorted(self.word_list, key=lambda w: w.number)
            if w.start.direction == d
        ]


def place_a_word(cells: Cells, w: Word, b: Bearing, commit: bool) -> True:
    cw = cells if commit else deepcopy(cells)
    d = b.direction
    for idx, letter in enumerate(w.word):
        p = b.position + d * idx
        try:
            c = cw[p]
        except KeyError:  # unfilled cell
            cw[p] = Cell(letter)
            continue
        if c.letter and c.letter != letter:
            raise CellOccupiedError
        if d is Direction.DOWN:
            if c.word_down:
                raise CellOccupiedError
            c.word_down = True
        elif d is Direction.ACROSS:
            if c.word_across:
                raise CellOccupiedError
            c.word_across = True
        cw[p] = Cell(letter)
    w.start = b
    return True


def read_crossword_file(f):
    r = DictReader(f, ["Word", "Hint", "Optional"], restval="F", dialect=excel_tab)
    for word in r:
        yield Word(
            word["Word"],
            word["Hint"],
            False if word["Optional"].strip()[0].upper() in "BOTE" else True,
        )


def generate_crossword(filename) -> ...:
    with open(filename) as f:
        return Crossword(read_crossword_file(f))


# TODO: check for isolated words


def random_crossword_words(n: int) -> list[Word]:
    """This is a test function that gives the answers as the hints"""
    return [
        Word(w, w, random.randint(1, 100) < 90) for w in get_random_words(n).split(",")
    ]


def display_for_terminal(w: Crossword):
    print("\n".join([" ".join(row) for row in w.solution_only()]))
    # for row in w.solution_only():
    #    print(row)
    print(f"Across:\n{w.hint_list(Direction.ACROSS)}")
    print(f"Down:\n{w.hint_list(Direction.DOWN)}")
    print("\n".join([" ".join(row) for row in w.terminal_display()]))


def test_failing_ws():
    display_for_terminal(Crossword(random_crossword_words(50)))


def read_test_file():
    display_for_terminal(generate_crossword("test-words1.tsv"))
