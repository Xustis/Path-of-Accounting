import tkinter

from gui.gui import ActiveWindow
from item.generator import Currency, Item
from utils.common import get_response, price_item
from utils.config import (
    GUI_BG1,
    GUI_BG2,
    GUI_FONT,
    GUI_FONT_COLOR,
    GUI_FONT_SIZE,
    LEAGUE,
    MIN_RESULTS,
)
from utils.web import open_exchange_site, open_trade_site


class AdvancedSearch(ActiveWindow):
    """Advanced Search Window"""

    def __init__(self):
        super().__init__()
        self.item = None
        self.selected = []

    def add_item(self, item):
        self.item = item
        self.selected = []

    def edit_item(self):
        nMods = []
        for mod in self.item.mods:
            if self.selected[mod[0].id].get():
                nMods.append(mod)
        self.item.mods = nMods
        self.item.print()

    def search(self):
        self.edit_item()
        price_item(self.item)
        self.close()

    def open_trade(self):
        self.edit_item()
        response = get_response(self.item)
        if response:
            if isinstance(self.item, Currency):
                open_exchange_site(response["id"], LEAGUE)
            else:
                open_trade_site(response["id"], LEAGUE)
        self.close()

    def add_components(self):
        """
        Add all of the components necessary for the GUI to display information.
        """

        if not isinstance(self.item, Item):
            return

        masterFrame = tkinter.Frame(self.frame, bg=GUI_BG1)
        masterFrame.place(relwidth=1, relheight=1)

        self.create_label_header("Advanced Search", 0, 0, "WE", 6)

        j = 0
        self.selected = {}
        self.entries = []
        if isinstance(self.item, Item):
            for mod in self.item.mods:
                self.selected[mod[0].id] = tkinter.StringVar()

                # CheckButton
                bgColor = GUI_BG2 if j % 2 else GUI_BG1
                cb = tkinter.Checkbutton(
                    self.frame,
                    text=mod[0].text,
                    variable=self.selected[mod[0].id],
                    bg=bgColor,
                    fg=GUI_FONT_COLOR,
                    activebackground=bgColor,
                    activeforeground=GUI_FONT_COLOR,
                )
                cb.select()
                cb.grid(row=j + 1, sticky="W", columnspan=3)
                cb.config(font=(GUI_FONT, GUI_FONT_SIZE))

                # Entry
                if mod[1]:  # If mod has values
                    val = tkinter.IntVar()
                    val.set(mod[1])
                    e = tkinter.Entry(
                        self.frame,
                        bg=bgColor,
                        fg=GUI_FONT_COLOR,
                        width=5,
                        textvariable=val,
                        exportselection=0,
                    )
                    e.grid(row=j + 1, column=4, sticky="E", columnspan=1)
                    val2 = tkinter.IntVar()
                    val2.set("max")
                    e2 = tkinter.Entry(
                        self.frame,
                        bg=bgColor,
                        fg=GUI_FONT_COLOR,
                        width=5,
                        textvariable=val2,
                        exportselection=0,
                    )
                    e2.grid(row=j + 1, column=5, sticky="E", columnspan=1)
                    self.entries.extend([e, e2])

                j += 1

        s = tkinter.Button(
            self.frame,
            text="Search",
            command=self.search,
            bg=GUI_BG1,
            fg=GUI_FONT_COLOR,
        )
        s.grid(column=0, row=j + 1, columnspan=2, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))
        s = tkinter.Button(
            self.frame,
            text="Open on Trade",
            command=self.open_trade,
            bg=GUI_BG1,
            fg=GUI_FONT_COLOR,
        )
        s.grid(column=2, row=j + 1, columnspan=2, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))
        s = tkinter.Button(
            self.frame,
            text="Close",
            command=self.close,
            bg=GUI_BG1,
            fg=GUI_FONT_COLOR,
        )
        s.grid(column=4, row=j + 1, columnspan=2, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))


advancedSearch = AdvancedSearch()
