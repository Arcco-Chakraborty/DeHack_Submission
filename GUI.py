from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.graphics import Color, Line
from kivy.clock import Clock

import math
import navigator


def draw_arrow(canvas, x1, y1, x2, y2, w=4):
    canvas.add(Line(points=[x1, y1, x2, y2], width=w, cap="round"))
    ang = math.atan2(y2 - y1, x2 - x1)
    l = 14
    a = math.pi / 6
    canvas.add(Line(points=[
        x2, y2,
        x2 - l * math.cos(ang - a), y2 - l * math.sin(ang - a)
    ], width=w))
    canvas.add(Line(points=[
        x2, y2,
        x2 - l * math.cos(ang + a), y2 - l * math.sin(ang + a)
    ], width=w))


class UI(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", spacing=6, padding=6, **kw)

        top = BoxLayout(size_hint=(1, .12), spacing=6)
        self.build = Spinner(text="Building", values=list(navigator.BUILDINGS))
        self.start = Spinner(text="Start")
        self.end = Spinner(text="End")
        top.add_widget(self.build)
        top.add_widget(self.start)
        top.add_widget(self.end)

        self.go = Button(text="NAVIGATE", size_hint=(1, .08))

        self.img = Image(allow_stretch=True, keep_ratio=True)

        bottom = BoxLayout(size_hint=(1, .1), spacing=10)
        self.down = Button(text="⬇ FLOOR")
        self.up = Button(text="⬆ FLOOR")
        bottom.add_widget(self.down)
        bottom.add_widget(self.up)

        self.add_widget(top)
        self.add_widget(self.go)
        self.add_widget(self.img)
        self.add_widget(bottom)

        self.build.bind(text=self.load_rooms)
        self.go.bind(on_press=self.run)
        self.up.bind(on_press=lambda *_: self.shift(1))
        self.down.bind(on_press=lambda *_: self.shift(-1))

        self.points = {}
        self.floors = []
        self.images = {}
        self.idx = 0

    def load_rooms(self, _, b):
        self.start.values = navigator.BUILDINGS[b]["rooms"]
        self.end.values = navigator.BUILDINGS[b]["rooms"]

    def run(self, _):
        self.points, self.floors, self.images, start_floor = navigator.navigate(
            self.build.text,
            self.start.text,
            self.end.text
        )

        if not self.floors:
            return

        # ✅ FIND INDEX OF START FLOOR
        self.idx = self.floors.index(start_floor)

        self.draw()

    def shift(self, d):
        if not self.floors:
            return
        self.idx = max(0, min(self.idx + d, len(self.floors) - 1))
        self.draw()

    def draw(self):
        if not self.floors:
            return

        f = self.floors[self.idx]
        self.img.source = self.images[f]
        self.img.reload()

        def paint(_):
            if not self.img.texture:
                return

            iw, ih = self.img.texture.size
            dw, dh = self.img.norm_image_size
            ox = self.img.center_x - dw / 2
            oy = self.img.center_y - dh / 2
            sx = dw / iw
            sy = dh / ih

            pts = []
            for i in range(0, len(self.points[f]), 2):
                x = self.points[f][i]
                y = self.points[f][i + 1]
                pts.append(ox + x * sx)
                pts.append(oy + (ih - y) * sy)

            self.img.canvas.after.clear()
            with self.img.canvas.after:
                Color(1, 0, 0, 0.95)
                for i in range(0, len(pts) - 2, 2):
                    draw_arrow(
                        self.img.canvas.after,
                        pts[i], pts[i + 1],
                        pts[i + 2], pts[i + 3]
                    )

        Clock.schedule_once(paint, 0)


class NavApp(App):
    def build(self):
        return UI()


NavApp().run()
