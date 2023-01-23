import tkinter as tk

buttons = [
    ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Backspace'],
    ['Tab', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\' ],
    ['Caps', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'Enter'],
    ['Shift', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'Clear'],
    ['Space']
 ]

capsButtons = [
    ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Backspace'],
    ['Tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\' ],
    ['Caps', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'", 'Enter'],
    ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'Clear'],
    ['Space']
 ]

uppercase = False
shiftActive = False

def create(root, entry):

    vkeyboard = tk.Toplevel(root)
    vkeyboard.minsize(1280, 280)
    vkeyboard.maxsize(1280, 280)
    vkeyboard.configure(background = "#080808")
    vkeyboard.protocol('WM_DELETE_WINOW', lambda: on_close(vkeyboard)) # Overwrites tkinter window delete for the keboard.

    root_x = root.winfo_x()
    root_y = root.winfo_y()
    vkeyboard.geometry("+%d+%d" %(root_x, root_y+440))
    vkeyboard.transient(root)
    def on_close(keybrd):
        global uppercase
        global shiftActive
        uppercase = False
        shiftActive = False
        keybrd.destroy()

    def keypress (entry, value):
        global uppercase
        global shiftActive

        if value == 'Space':
            value = ' '
        # Since none of the text entry fields in the DAQ_GUI take more than one line,
        # Enter is used as another way to exit from the keyboard and/or finish input.
        elif value == 'Enter':
            value = ''
            on_close(vkeyboard)
        elif value == 'Tab':
            value = '\t'
        if value == 'Backspace':
            entry.delete(len(entry.get())-1, 'end')
        elif value == 'Clear':
            entry.delete(0, 'end')
        elif value == 'Caps':
            if uppercase is True:
                uppercase = not uppercase
                draw(vkeyboard, buttons)
            else:
                uppercase = not uppercase
                draw(vkeyboard, capsButtons)

        elif value == 'Shift':
            if uppercase is False:
                uppercase = not uppercase
                shiftActive = not shiftActive
                draw(vkeyboard, capsButtons)
            elif uppercase is True:
                uppercase = not uppercase
                draw(vkeyboard, buttons)

        else:
            if shiftActive is True:
                shiftActive = not shiftActive
                uppercase = not uppercase
                draw(vkeyboard, buttons)
            entry.insert('end', value)

    # Creates (or re-creates) the keyboard buttons and their grid.
    def draw(keybrd, btn):
        for y, row in enumerate(btn):
            x = 1

            for key in row:
                if key == 'Enter':
                    width = 8
                    columnspan = 2
                elif key == 'Caps':
                    width = 11
                    columnspan = 2
                elif key == 'Shift':
                    width = 11
                    columnspan = 2
                elif key == 'Clear':
                    width = 11
                    columnspan = 2
                elif key == 'Backspace':
                    width = 9
                    columnspan = 2
                elif key == 'Space':
                    width = 100
                    columnspan = 16
                else:
                    width = 4
                    columnspan = 1

                tk.Button(keybrd, text = key, width = width, command = lambda value = key: keypress(entry, value),
                          padx = 5, pady = 5, bd = 9, bg = "#4D4F52", fg = "white",
                          font = ('Comic Sans', 11)).grid(row = y, column = x, columnspan = columnspan, sticky = 'sw')

                x += columnspan
        keybrd.grid_columnconfigure(0, minsize = 140)
        keybrd.grid_rowconfigure(0, pad = 10)
        keybrd.transient(root)
        keybrd.overrideredirect(True)
        keybrd.wait_visibility()
        keybrd.grab_set()

    draw(vkeyboard, buttons)