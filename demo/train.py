import json
import time
from os import getenv

import numpy as np
import requests
from dotenv import load_dotenv

from demo.sample_demo import Demo
from flippy.text_rendering import TextAlign, TextRenderer, MINECRAFT, NEWBASIC_3X5_KERN


class TrainDemo(Demo):
    """Demo of displaying text on the sign. This uses one of my other projects (trainTable) as the data source"""

    def run(self):
        load_dotenv()

        if (key := getenv("TRAINTABLE_KEY")) is None:
            raise ValueError("TRAINTABLE_KEY not specified in .env file!")

        origin = input("Origin (CRS)? ").upper()
        destination = input("Destination (CRS)? ").upper()
        if destination == "":
            destination = "ANY"
        renderer = TextRenderer(MINECRAFT, self._sign.shape)
        renderer_2 = TextRenderer(NEWBASIC_3X5_KERN, self._sign.shape)
        base_state = renderer.text(f"{origin}>{destination}", align=TextAlign.LEFT)

        try:
            while True:
                t1, t2 = self._get_train(origin, destination, key)
                times = np.zeros(self._sign.shape)
                times[:, :-1] = renderer_2.text(f"{t1}, {t2}", align=TextAlign.RIGHT)[
                    :, 1:
                ]
                self._sign.state = base_state + times
                self._sign.update()
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        input("Press enter to exit...")

    @staticmethod
    def _get_train(og, dst, key):
        response = requests.get(
            f"https://tt.nthn.uk/ldb/dep/{og}/{dst}?token={key}&filter=true&filter_formation=true"
        )
        if response.status_code == 200:
            trains = json.loads(response.text)
            s = trains["services"]  # list of upcoming departures

            # depending on what data is available, different fields will be filled for the best-estimate of departure
            # time possible.
            times = [
                t.get("expected_departure", t.get("actual_departure", "T???")).split(
                    "T"
                )[1][:5]
                for t in s
            ]
            times = [t for t in times if t != "???"]
            if len(times) == 0:
                return "---", "---"
            elif len(times) == 1:
                return times[0], "---"
            else:
                return times[0], times[1]

        return "---", "---"

    def cleanup(self):
        self._sign.clear()
