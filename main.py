import os
import sys
import sqlite3
import traceback
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.core.text import Label as CoreLabel


class GraphWidget(Widget):
    """Виджет для отрисовки графика динамики давления и пульса на Canvas."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []
        self.bind(pos=self.draw_graph, size=self.draw_graph)

    def set_data(self, data):
        self.data = data[-12:]
        self.draw_graph()

    def _draw_text(self, text, x, y, font_size=11, color=(0.85, 0.85, 0.85, 1)):
        try:
            lbl = CoreLabel(text=str(text), font_size=sp(font_size))
            lbl.refresh()
            tex = lbl.texture
            if tex:
                Color(*color)
                Rectangle(texture=tex, pos=(x, y), size=tex.size)
                return tex.size
        except Exception as e:
            print(f"Text render error: {e}")
        return (0, 0)

    def draw_graph(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.14, 0.15, 0.18, 1)
            Rectangle(pos=self.pos, size=self.size)

            if not self.data:
                self._draw_text(
                    "Нет данных. Добавьте первое измерение.",
                    self.center_x - dp(110),
                    self.center_y,
                    font_size=13
                )
                return

            pad_left = dp(40)
            pad_right = dp(20)
            pad_bottom = dp(45)
            pad_top = dp(35)

            plot_w = self.width - pad_left - pad_right
            plot_h = self.height - pad_bottom - pad_top
            if plot_w <= 0 or plot_h <= 0:
                return

            x0 = self.x + pad_left
            y0 = self.y + pad_bottom

            all_vals = []
            for _, sys_v, dia_v, pulse_v in self.data:
                all_vals.extend([sys_v, dia_v, pulse_v])

            min_val = max(30, (min(all_vals) // 10) * 10 - 10)
            max_val = (max(all_vals) // 10) * 10 + 20
            val_range = max(max_val - min_val, 10)

            steps = 5
            for i in range(steps + 1):
                val = int(min_val + (val_range / steps) * i)
                y = y0 + (i / steps) * plot_h
                Color(0.28, 0.3, 0.35, 1)
                Line(points=[x0, y, x0 + plot_w, y], width=1)
                self._draw_text(str(val), self.x + dp(6), y - dp(7), font_size=10)

            legend_y = self.top - dp(22)
            self._draw_text("■ Верхнее", x0, legend_y, font_size=11, color=(1, 0.35, 0.35, 1))
            self._draw_text("■ Нижнее", x0 + dp(85), legend_y, font_size=11, color=(0.3, 0.65, 1, 1))
            self._draw_text("■ Пульс", x0 + dp(165), legend_y, font_size=11, color=(0.3, 0.9, 0.5, 1))

            n = len(self.data)
            step_x = plot_w / (n - 1) if n > 1 else 0

            def get_xy(idx, val):
                px = x0 + (idx * step_x if n > 1 else plot_w / 2)
                py = y0 + ((val - min_val) / val_range) * plot_h
                return px, py

            sys_pts, dia_pts, pulse_pts = [], [], []

            for i, (dt_iso, sys_v, dia_v, pulse_v) in enumerate(self.data):
                sx, sy = get_xy(i, sys_v)
                dx, dy = get_xy(i, dia_v)
                px, py = get_xy(i, pulse_v)

                sys_pts.extend([sx, sy])
                dia_pts.extend([dx, dy])
                pulse_pts.extend([px, py])

                if n <= 6 or i % 2 == 0 or i == n - 1:
                    try:
                        dt_obj = datetime.strptime(dt_iso, "%Y-%m-%d %H:%M")
                        short_dt = dt_obj.strftime("%d.%m\n%H:%M")
                    except ValueError:
                        short_dt = dt_iso[-5:]
                    self._draw_text(short_dt, sx - dp(14), self.y + dp(4), font_size=9)

            if n > 1:
                Color(1, 0.35, 0.35, 1)
                Line(points=sys_pts, width=dp(1.8))
                Color(0.3, 0.65, 1, 1)
                Line(points=dia_pts, width=dp(1.8))
                Color(0.3, 0.9, 0.5, 1)
                Line(points=pulse_pts, width=dp(1.5))

            r = dp(4)
            for i in range(n):
                Color(1, 0.35, 0.35, 1)
                sx, sy = sys_pts[2 * i], sys_pts[2 * i + 1]
                Ellipse(pos=(sx - r, sy - r), size=(r * 2, r * 2))
                self._draw_text(self.data[i][1], sx - dp(8), sy + dp(4), font_size=9, color=(1, 0.5, 0.5, 1))

                Color(0.3, 0.65, 1, 1)
                dx, dy = dia_pts[2 * i], dia_pts[2 * i + 1]
                Ellipse(pos=(dx - r, dy - r), size=(r * 2, r * 2))
                self._draw_text(self.data[i][2], dx - dp(8), dy + dp(4), font_size=9, color=(0.5, 0.8, 1, 1))

                Color(0.3, 0.9, 0.5, 1)
                px, py = pulse_pts[2 * i], pulse_pts[2 * i + 1]
                Ellipse(pos=(px - r, py - r), size=(r * 2, r * 2))
                self._draw_text(self.data[i][3], px - dp(8), py - dp(15), font_size=9, color=(0.5, 1, 0.6, 1))


class BPTrackerApp(App):
    def build(self):
        self.title = "Дневник давления и пульса"

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        # --- Блок ввода давления и пульса ---
        inputs_grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(70))
        self.sys_input = self._create_num_input("Верхнее\n(120)")
        self.dia_input = self._create_num_input("Нижнее\n(80)")
        self.pulse_input = self._create_num_input("Пульс\n(70)")

        inputs_grid.add_widget(self.sys_input)
        inputs_grid.add_widget(self.dia_input)
        inputs_grid.add_widget(self.pulse_input)
        root.add_widget(inputs_grid)

        # --- Переключатель режима даты и времени ---
        mode_box = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(42))
        self.auto_btn = ToggleButton(
            text="Время: Авто",
            group="dt_mode",
            state="down",
            font_size=sp(13)
        )
        self.manual_btn = ToggleButton(
            text="Время: Вручную",
            group="dt_mode",
            state="normal",
            font_size=sp(13)
        )
        self.auto_btn.bind(on_press=self.update_dt_mode)
        self.manual_btn.bind(on_press=self.update_dt_mode)

        mode_box.add_widget(self.auto_btn)
        mode_box.add_widget(self.manual_btn)
        root.add_widget(mode_box)

        # --- Поля даты и времени ---
        dt_box = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(44))
        now = datetime.now()
        self.date_input = TextInput(
            text=now.strftime("%d.%m.%Y"),
            hint_text="ДД.ММ.ГГГГ",
            multiline=False,
            disabled=True,
            font_size=sp(15),
            halign="center"
        )
        self.time_input = TextInput(
            text=now.strftime("%H:%M"),
            hint_text="ЧЧ:ММ",
            multiline=False,
            disabled=True,
            font_size=sp(15),
            halign="center"
        )
        dt_box.add_widget(self.date_input)
        dt_box.add_widget(self.time_input)
        root.add_widget(dt_box)

        # --- Кнопки действий ---
        btn_box = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(48))
        save_btn = Button(
            text="Сохранить запись",
            background_color=(0.2, 0.7, 0.4, 1),
            font_size=sp(15),
            bold=True
        )
        save_btn.bind(on_press=self.save_record)

        del_btn = Button(
            text="Удалить последнюю",
            size_hint_x=0.55,
            background_color=(0.8, 0.3, 0.3, 1),
            font_size=sp(12)
        )
        del_btn.bind(on_press=self.delete_last_record)

        btn_box.add_widget(save_btn)
        btn_box.add_widget(del_btn)
        root.add_widget(btn_box)

        # --- Статусная строка ---
        self.status_label = Label(
            text="Введите показатели и нажмите «Сохранить»",
            size_hint_y=None,
            height=dp(26),
            font_size=sp(13),
            color=(0.8, 0.85, 0.9, 1)
        )
        root.add_widget(self.status_label)

        # --- График динамики ---
        self.graph = GraphWidget(size_hint_y=1)
        root.add_widget(self.graph)

        return root

    def on_start(self):
        # Инициализируем базу данных и загружаем график только когда окно полностью готово
        Clock.schedule_once(self._post_init, 0.1)

    def _post_init(self, dt):
        try:
            self.init_db()
            self.load_data()
        except Exception as e:
            self.status_label.text = f"Ошибка инициализации: {e}"
            self.status_label.color = (1, 0.2, 0.2, 1)

    def _create_num_input(self, hint):
        return TextInput(
            hint_text=hint,
            input_filter="int",
            multiline=False,
            font_size=sp(16),
            halign="center",
            padding=[dp(6), dp(12)]
        )

    def get_db_path(self):
        db_dir = self.user_data_dir
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "bp_records.db")

    def init_db(self):
        with sqlite3.connect(self.get_db_path()) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dt_iso TEXT NOT NULL,
                    sys INTEGER NOT NULL,
                    dia INTEGER NOT NULL,
                    pulse INTEGER NOT NULL
                )
            """)

    def update_dt_mode(self, instance):
        if self.auto_btn.state == "normal" and self.manual_btn.state == "normal":
            instance.state = "down"

        is_auto = self.auto_btn.state == "down"
        self.date_input.disabled = is_auto
        self.time_input.disabled = is_auto

        if is_auto:
            now = datetime.now()
            self.date_input.text = now.strftime("%d.%m.%Y")
            self.time_input.text = now.strftime("%H:%M")

    def save_record(self, *args):
        sys_txt = self.sys_input.text.strip()
        dia_txt = self.dia_input.text.strip()
        pulse_txt = self.pulse_input.text.strip()

        if not (sys_txt and dia_txt and pulse_txt):
            self.status_label.text = "Ошибка: заполните все поля давления и пульса!"
            self.status_label.color = (1, 0.4, 0.4, 1)
            return

        sys_val, dia_val, pulse_val = int(sys_txt), int(dia_txt), int(pulse_txt)
        if not (40 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pulse_val <= 250):
            self.status_label.text = "Ошибка: проверьте реалистичность значений!"
            self.status_label.color = (1, 0.4, 0.4, 1)
            return

        if self.auto_btn.state == "down":
            dt_obj = datetime.now()
            self.date_input.text = dt_obj.strftime("%d.%m.%Y")
            self.time_input.text = dt_obj.strftime("%H:%M")
        else:
            dt_raw = f"{self.date_input.text.strip()} {self.time_input.text.strip()}"
            try:
                dt_obj = datetime.strptime(dt_raw, "%d.%m.%Y %H:%M")
            except ValueError:
                self.status_label.text = "Ошибка формата! Используйте ДД.ММ.ГГГГ и ЧЧ:ММ"
                self.status_label.color = (1, 0.4, 0.4, 1)
                return

        dt_iso = dt_obj.strftime("%Y-%m-%d %H:%M")

        with sqlite3.connect(self.get_db_path()) as conn:
            conn.execute(
                "INSERT INTO records (dt_iso, sys, dia, pulse) VALUES (?, ?, ?, ?)",
                (dt_iso, sys_val, dia_val, pulse_val)
            )

        self.sys_input.text = ""
        self.dia_input.text = ""
        self.pulse_input.text = ""

        self.status_label.text = f"Сохранено: {sys_val}/{dia_val}, пульс {pulse_val} ({dt_obj.strftime('%d.%m %H:%M')})"
        self.status_label.color = (0.4, 1, 0.5, 1)
        self.load_data()

    def delete_last_record(self, *args):
        with sqlite3.connect(self.get_db_path()) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM records ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                conn.execute("DELETE FROM records WHERE id = ?", (row[0],))
                self.status_label.text = "Последняя добавленная запись удалена."
                self.status_label.color = (1, 0.8, 0.4, 1)
            else:
                self.status_label.text = "База данных уже пуста."
                self.status_label.color = (0.8, 0.8, 0.8, 1)
        self.load_data()

    def load_data(self):
        with sqlite3.connect(self.get_db_path()) as conn:
            cur = conn.cursor()
            cur.execute("SELECT dt_iso, sys, dia, pulse FROM records ORDER BY dt_iso ASC")
            rows = cur.fetchall()
        self.graph.set_data(rows)


if __name__ == "__main__":
    try:
        BPTrackerApp().run()
    except Exception:
        # При аварии пишем трассировку в файл и в stderr для logcat
        traceback.print_exc()
        try:
            with open(os.path.expanduser("~/bp_crash.log"), "w") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
