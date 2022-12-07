from math import sqrt
from typing import Iterable
from csv import DictReader, excel_tab

from word_search_generator import WordSearch, MissingWordError, Puzzle, Direction
from word_search_generator.utils import get_random_words, format_puzzle_for_show
from word_search_generator.word import Position

BOUNDARY_CELL = "B"
VOID_CELL = "X"
WORD_CELL = " "


def read_crossword_file(f):
    words = {}
    optional_words = {}
    r = DictReader(f, ["Word", "Hint", "Optional"], restval="F", dialect=excel_tab)
    for word in r:
        if word["Optional"].strip()[0].upper() in "BOTE":
            optional_words[word["Word"]] = word["Hint"]
        else:
            words[word["Word"]] = word["Hint"]
    return words, optional_words


def sort_word_dict_by_length(wd: dict[str, str]) -> list[str]:
    return sorted(list(wd.keys()), key=lambda x: len(x), reverse=True)


def count_characters_in_word_list(words: Iterable[str]) -> int:
    return sum(len(w) for w in words)


def get_cell(p: Puzzle, row: int, col: int) -> str:
    if row < 0 or col < 0:
        return BOUNDARY_CELL
    try:
        return p[row][col]
    except IndexError:
        return BOUNDARY_CELL


def get_neighboring_cells(p: Puzzle, row: int, col: int) -> set[str]:
    """This one only cares about N, E, W, and S"""
    return {
        get_cell(p, row - 1, col),  # N
        get_cell(p, row, col + 1),  # E
        get_cell(p, row, col - 1),  # W
        get_cell(p, row + 1, col),  # S
    }


def normalize_input(d: dict[str, str]) -> dict[str, str]:
    return {key.strip().upper(): val.strip() for key, val in d.items()}


class Crossword(WordSearch):
    def __init__(
        self, words: dict[str, str], optional_words: dict[str, str] | None = None
    ):

        if not optional_words:
            optional_words = {}
        lengths = sorted([len(w) for w in (words.keys() | optional_words.keys())])
        size = max(
            lengths[-1],
            round(sqrt(sum(lengths)) + 1),
        )
        self.across: dict[int, str] = {}
        self.down: dict[int, str] = {}
        self.word_list: dict[str, str] = normalize_input(optional_words | words)
        self.crossword: Puzzle = []

        attempt = 0
        while True:
            try:
                self.crossword = [["X"] * size for _ in range(size)]
                super().__init__(
                    " ".join(words.keys()),
                    1,
                    size,
                    " ".join(optional_words.keys()),
                    include_all_words=True,
                )
            except MissingWordError:
                if True is False:  # leave in for future debugging
                    print(
                        f"Size {size} attempt {attempt} failed"
                        + f"\nMissing words: {self.unplaced_hidden_words}"
                    )
                attempt += 1
                if attempt > 3:
                    size += 1
                    attempt = 0
            if not self.unplaced_hidden_words:
                break  # mission success

    def make_lattice(self) -> None:
        f"""
        Makes the Crossword lattice.  Each cell contains one of the following:
            - {VOID_CELL} = Blocked-off cell
            - {BOUNDARY_CELL} = OOB boundary cell
            - a number = starting position for a word
            - a space = empty cell for a word
        """
        index = 0
        previous_position = Position(-1, -1)
        for word in sorted(self.placed_words, key=lambda w: w.position):
            if word.position != previous_position:
                index += 1
                previous_position = word.position
                self.crossword[word.start_row][word.start_column] = str(index)
            if word.direction == Direction.S:
                self.down[index] = self.word_list[word.text]
                for offset in range(1, len(word.text)):
                    self.crossword[word.start_row + offset][
                        word.start_column
                    ] = WORD_CELL
            else:
                self.across[index] = self.word_list[word.text]
                for offset in range(1, len(word.text)):
                    self.crossword[word.start_row][
                        word.start_column + offset
                    ] = WORD_CELL

        # split out the internal and boundary-touching blocked-out regions
        for row_num, row in enumerate(self.crossword):
            for col_num, char in enumerate(row):
                if char == VOID_CELL and BOUNDARY_CELL in get_neighboring_cells(
                    self.crossword, row_num, col_num
                ):
                    row[col_num] = BOUNDARY_CELL

    def _generate(self, fill_puzzle: bool = True) -> None:
        super()._generate(fill_puzzle)
        self.make_lattice()


def generate_crossword(filename) -> ...:
    with open(filename) as f:
        return Crossword(*read_crossword_file(f))


# TODO: check for isolated words


def random_crossword_words(n: int) -> dict[str, str]:
    """This is a test function that gives the answers as the hints"""
    return {w: w for w in get_random_words(n).split(",")}


def display_for_terminal(w: Crossword):
    print("\n".join([" ".join(row) for row in w.crossword]))
    print(f"Across:\n{w.across}")
    print(f"Down:\n{w.down}")


def test_failing_ws():
    display_for_terminal(Crossword(random_crossword_words(50), random_crossword_words(12)))


def read_test_file():
    display_for_terminal(generate_crossword("test-words1.tsv"))
