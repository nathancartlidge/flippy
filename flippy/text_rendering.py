"""
This class is an adapter function to allow fonts originally provided with the
repository https://github.com/greiman/SSD1306Ascii to be used here
"""

from enum import Enum

import numpy as np

from flippy.font_data import ADAFRUIT_5X7_DATA


class Font:
    """Class to store fonts"""
    def __init__(self, font_data: list, num_chars: int, height: int,
                 space_width: int = 2, alternate_mode: bool = False):
        if height > 16:
            raise ValueError("This class does not yet support fonts larger than 16px tall")
        self._height = height
        self._font_data = font_data
        self._num_chars = num_chars
        self._space_width = space_width
        self._alternate_mode = alternate_mode

    @property
    def num_chars(self):
        """Returns the number of characters in the font set"""
        return self._num_chars

    @property
    def height(self):
        """Returns the height of the font in pixels"""
        return self._height

    def _char(self, character):
        """Font data for a particular character"""
        if ord(character) > self.num_chars:
            raise ValueError("Error: invalid char!")

        raw_data = self._font_data[ord(character)]
        if character == " ":
            raw_data = [0x00] * self._space_width

        if self.height <= 8:
            return [self._small_font_convert_line(x) for x in raw_data]
        else:
            char_midpoint = int(len(raw_data) / 2)
            return [self._large_font_convert_line(x, y)
                    for x, y in zip(raw_data[:char_midpoint],
                                    raw_data[char_midpoint:])]

    def string(self, string: str, ignore_errors: bool = False):
        """Generates the representation of a string of characters"""
        output = []
        for i, char in enumerate(string):
            try:
                representation = self._char(char)
            except ValueError:
                if not ignore_errors:
                    raise
                else:
                    continue
            output.extend(representation)
            if i != len(string):
                output.append([0x00] * self.height)
        return np.array(output)

    def _small_font_convert_line(self, code):
        """Parses fonts under 8px tall to the correct format"""
        arr = []
        code_string = f'{code:8b}'.replace(' ', '0')
        for pixel in code_string:
            arr.append(int(pixel))
        return arr[-self.height::][::-1]

    def _large_font_convert_line(self, code_1, code_2):
        """Parses fonts between 8px and 16px tall to the correct format"""
        arr = []
        code_string = f'{code_1:8b}'.replace(' ', '0')
        code_string_2 = f'{code_2:8b}'.replace(' ', '0')
        if self._alternate_mode:
            code_string = code_string[-(16 - self.height)::-1] + code_string_2[:0:-1]
        else:
            code_string = code_string[::-1] + code_string_2[-(1 + 16 - self.height)::-1]
        for pixel in code_string:
            arr.append(int(pixel))
        return arr

    @staticmethod
    def preview(data: np.ndarray):
        """Format the data for validation purposes"""
        output_string = ""
        for line in data.T:
            for char in line:
                output_string += [' ', '█'][char] * 2
            output_string += "\n"

        print(output_string)


class TextAlign(Enum):
    LEFT = 0
    RIGHT = 1
    CENTER = 2


class TextRenderer:
    def __init__(self, font: Font, shape: tuple[int, int]):
        self._font = font
        self._shape = shape

    @property
    def font(self):
        return self._font

    @property
    def shape(self):
        return self._shape

    def text(self, text: str, align: TextAlign = TextAlign.CENTER,
             allow_clip: bool = False):
        """renders a single screen of text"""
        screen = np.full(self.shape, False, dtype=bool)
        rendered_text = self._font.string(text)

        if not allow_clip and rendered_text.shape[0] > screen.shape[0]:
            raise ValueError("Text does not fit on screen")

        width = min(screen.shape[0], rendered_text.shape[0])
        height = min(screen.shape[1], rendered_text.shape[1])
        rendered_text = rendered_text[0:width, 0:height]

        # todo: allow offset y
        if align is TextAlign.LEFT:
            screen[0:width, 0:height] = rendered_text
        elif align is TextAlign.RIGHT:
            screen[self.shape[0] - width:self.shape[0], 0:height] = rendered_text
        elif align is TextAlign.CENTER:
            start = (self.shape[0] - width) // 2
            screen[start:start+width, 0:height] = rendered_text
        else:
            raise ValueError("Unknown Alignment")

        return screen

    def long_text(self, text: str, align: TextAlign = TextAlign.CENTER) -> list[np.ndarray]:
        """Splits a long message into multiple screens of text"""
        words = text.split(" ")
        if len(words) == 0:
            return []

        output = []
        counter = 0
        while counter < len(words):
            added_words = [words[counter]]
            while self._font.string(" ".join(added_words)).shape[1] <= self.shape[1]:
                if counter + len(added_words) == len(words):
                    break

                added_words.append(words[counter + len(added_words)])

            if len(added_words) > 1:
                added_words.pop()

            counter += len(added_words)
            output.append(self.text(" ".join(added_words), align))

        return output


ADAFRUIT_5X7 = Font(ADAFRUIT_5X7_DATA, 255, 8)
