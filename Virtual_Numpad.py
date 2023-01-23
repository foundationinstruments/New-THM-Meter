import tkinter as tk

numpadButtons = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['0', 'Del', 'Enter'],
    ['.', 'Clear']
 ]

def create(root, entry, x_offset, y_offset):

    vnumpad = tk.Toplevel(root)
    vnumpad.minsize(263, 280)
    vnumpad.maxsize(263, 280)
    vnumpad.configure(background = "#080808")

    root_x = root.winfo_x()
    root_y = root.winfo_y()
    vnumpad.geometry("+%d+%d" %(root_x+x_offset, root_y+y_offset))

    def buttonpress(entry, value):
        if value == 'Enter':
            value = ''
            vnumpad.destroy()
        elif value == 'Del':
            entry.delete(len(entry.get())-1, 'end')
        elif value == 'Clear':
            entry.delete(0, 'end')
        else:
            entry.insert('end', value)

    # Creates the numpad buttons and their grid.
    def draw(numpad, btn):
        for y, row in enumerate(btn):
            x = 1

            for button in row:
                if button == 'Clear':
                    width = 10
                    columnspan = 2
                else:
                    width = 4
                    columnspan = 1

                tk.Button(numpad, text = button, width = width, command = lambda value = button: buttonpress(entry, value),
                          padx = 6, pady = 6, bd = 3, bg = "#4D4F52", fg = "white",
                          font = ('Comic Sans', 17)).grid(row = y, column = x, columnspan = columnspan, padx = 2, pady = 1,
                                                          sticky = 'sw')

                x += columnspan

        numpad.grid_columnconfigure(0, minsize = 7)
        numpad.grid_rowconfigure(0, pad = 7)
        numpad.transient(root)
        numpad.overrideredirect(True)
        numpad.wait_visibility()
        numpad.grab_set()


    draw(vnumpad, numpadButtons)