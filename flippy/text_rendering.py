"""
This class contains adapter functions (`BinaryFont` and `BitmapFont`) to allow
font files from other sources (SSD1306ASCII and Minecraft/similar games
respectively as a source of text
"""
import pathlib
from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from flippy.font_data import ADAFRUIT_5X7_DATA, NEWBASIC_3X5_DATA, WENDY_3X5_DATA


class Font:
    """Class to store fonts"""
    def __init__(self, height: int, num_chars: int, space_width: int = 1, offset: int = 0):
        self._height = height
        self._offset = offset
        self._num_chars = num_chars
        self._space_width = space_width

    @property
    def num_chars(self):
        """Returns the number of characters in the font set"""
        return self._num_chars

    @property
    def height(self):
        """Returns the height of the font in pixels"""
        return self._height

    @abstractmethod
    def char(self, character):
        """Outputs the font data for a particular character as a numpy array"""
        raise NotImplementedError

    def string(self, string: str, ignore_errors: bool = False):
        """
        Based upon the `char` function, generate the representation of a string
        of characters
        """
        output = []
        for i, char in enumerate(string):
            try:
                representation = self.char(char)
            except ValueError:
                if not ignore_errors:
                    raise
                else:
                    continue
            output.extend(representation)

            if i != len(string) - 1:  # do not output a gap after the last character
                # a one-pixel horizontal between letters
                output.append([0x00] * self.height)

        return np.array(output)

    @staticmethod
    def preview(data: np.ndarray):
        """Format the data for validation purposes"""
        output_string = ""
        for line in data.T:
            for char in line:
                output_string += [' ', '█'][char] * 2
            output_string += "\n"

        print(output_string)


class BinaryFont(Font):
    """Fonts adapted from https://github.com/greiman/SSD1306Ascii data"""
    def __init__(self, font_data: list, height: int, space_width: int = 2,
                 alternate_mode: bool = False, kern: bool = False, offset: int = 0):
        if height > 16:
            raise ValueError("This class does not yet support fonts larger than 16px tall")
        super().__init__(height, len(font_data), space_width=space_width, offset=offset)

        self._alternate_mode = alternate_mode
        self._font_data = font_data
        self._kern = kern

    def char(self, character):
        """Font data for a particular character"""
        if ord(character) - self._offset > self.num_chars:
            raise ValueError(f"Error: invalid char '{character}'!")

        raw_data = self._font_data[ord(character) - self._offset]

        if self.height <= 8:
            if character == " ":
                raw_data = [0x00] * self._space_width
            elif self._kern:
                raw_data = self._apply_kerning(raw_data)

            return [self._small_font_convert_line(x) for x in raw_data]
        else:
            if character == " ":
                raw_data = [0x00] * self._space_width * 2
            elif self._kern:
                raw_data = self._apply_kerning(raw_data, group=True)

            char_midpoint = int(len(raw_data) / 2)
            return [self._large_font_convert_line(x, y)
                    for x, y in zip(raw_data[:char_midpoint],
                                    raw_data[char_midpoint:])]

    @staticmethod
    def _apply_kerning(raw_data: list[int], group: bool = False):
        i = 0
        j = len(raw_data)

        if group:
            while i < j and raw_data[i] == 0x00 and raw_data[i + 1] == 0x00:
                i += 2
            while j >= i and raw_data[j - 1] == 0x00 and raw_data[j - 2] == 0x00:
                j -= 2
        else:
            while i < j and raw_data[i] == 0x00:
                i += 1
            while j >= i and raw_data[j - 1] == 0x00:
                j -= 1

        return raw_data[i:j]

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


class BitmapFont(Font):
    """Fonts adapted from https://github.com/greiman/SSD1306Ascii data"""

    def __init__(self, path: Path, size: int = 8, space_width: int = 2,
                 kern: bool = True):
        self._size = size
        self._bitmap = Image.open(path)

        self._dimensions = (self._bitmap.width // size, self._bitmap.height // size)
        if self._bitmap.mode not in ("1", "L", "P"):
            raise ValueError("Unsupported colour space")

        super().__init__(height=size, num_chars=self._dimensions[0] * self._dimensions[1], space_width=space_width)
        self._kern = kern

    def char(self, character):
        """Font data for a particular character"""
        if ord(character) - self._offset > self.num_chars:
            raise ValueError(f"Error: invalid char '{character}'!")
        elif character == " ":
            return np.zeros((self._space_width, self.height), dtype=np.uint8)

        char_offset = ord(character) - self._offset
        x = self._size * (char_offset % self._dimensions[0])
        y = self._size * (char_offset // self._dimensions[0])
        pixels = np.array(self._bitmap)[y:y+self._size, x:x+self._size]

        if self._kern:
            pixels = self._apply_kerning(pixels)

        return pixels.T

    @staticmethod
    def _apply_kerning(character_pixels: np.ndarray):
        pixel_rows = []
        for row in character_pixels.T:
            pixel_rows.append(row)

        # remove lines of pixels from the start
        for row in pixel_rows:
            if sum(row) == 0:
                pixel_rows.pop(0)
            else:
                break

        # remove lines of empty pixels from the end
        for row in pixel_rows[::-1]:
            if sum(row) == 0:
                pixel_rows.pop()
            else:
                break

        return np.array(pixel_rows).T


class TextAlign(Enum):
    LEFT = 0
    RIGHT = 1
    CENTRE = 2


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

    def text(self, text: str, align: TextAlign = TextAlign.CENTRE,
             allow_clip: bool = False):
        """renders a single screen of text"""
        screen = np.full(self.shape, False, dtype=bool)
        if text == "":
            return screen
        rendered_text = self._font.string(text)

        if not allow_clip and rendered_text.shape[0] > screen.shape[0]:
            raise ValueError(f"Text '{text}' cannot fit on screen")

        width = min(screen.shape[0], rendered_text.shape[0])
        height = min(screen.shape[1], rendered_text.shape[1])
        rendered_text = rendered_text[0:width, 0:height]

        # todo: allow offset y
        if align is TextAlign.LEFT:
            screen[0:width, 0:height] = rendered_text
        elif align is TextAlign.RIGHT:
            screen[self.shape[0] - width:self.shape[0], 0:height] = rendered_text
        elif align is TextAlign.CENTRE:
            start = (self.shape[0] - width) // 2
            screen[start:start+width, 0:height] = rendered_text
        else:
            raise ValueError("Unknown Alignment")

        return screen

    def long_text(self, text: str, align: TextAlign = TextAlign.CENTRE, allow_clip: bool = True) \
            -> list[tuple[Optional[np.ndarray], str]]:
        """Splits a long message into multiple screens of text"""
        words = text.split(" ")
        if len(words) == 0:
            return []

        output = []
        counter = 0
        while counter < len(words):
            added_words = [words[counter]]
            while text_fits := (self._font.string(" ".join(added_words)).shape[0] <= self.shape[0]):
                if counter + len(added_words) == len(words):
                    break

                added_words.append(words[counter + len(added_words)])

            if not text_fits and len(added_words) > 1:
                added_words.pop()

            if len(added_words) == 0:
                output.append((None, ""))
            else:
                counter += len(added_words)
                screen_words = " ".join(added_words)
                output.append((self.text(screen_words, align, allow_clip=allow_clip), screen_words))

        return output


ADAFRUIT_5X7 = BinaryFont(ADAFRUIT_5X7_DATA, space_width=1, height=8)
ADAFRUIT_5X7_KERN = BinaryFont(ADAFRUIT_5X7_DATA, space_width=1, height=8, kern=True)
NEWBASIC_3X5 = BinaryFont(NEWBASIC_3X5_DATA, space_width=1, height=8, offset=32)
NEWBASIC_3X5_KERN = BinaryFont(NEWBASIC_3X5_DATA, space_width=1, height=8, kern=True, offset=32)
WENDY_3X5 = BinaryFont(WENDY_3X5_DATA, space_width=1, height=5, offset=32)
WENDY_3X5_KERN = BinaryFont(WENDY_3X5_DATA, space_width=1, height=5, kern=True, offset=32)

# this is not bundled, but can be found from a default minecraft texture pack
#  (e.g. https://www.curseforge.com/minecraft/texture-packs/vanilladefault)
#  as assets/minecraft/textures/font/ascii.png
MINECRAFT = None
minecraft_font_path = pathlib.Path(__file__).parent.joinpath("minecraft_font.png")
if minecraft_font_path.exists():
    MINECRAFT = BitmapFont(minecraft_font_path, space_width=1)

MINECRAFT_ENCHANT = None
minecraft_enchant_font_path = pathlib.Path(__file__).parent.joinpath("minecraft_enchant_font.png")
if minecraft_enchant_font_path.exists():
    MINECRAFT_ENCHANT = BitmapFont(minecraft_enchant_font_path, space_width=1)
