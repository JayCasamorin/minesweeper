import tkinter as tk
import random
import numpy as np
from tkinter import messagebox, simpledialog
import threading

class Minesweeper(tk.Frame):
    def __init__(self, master, board_size):
        super().__init__(master)
        self.master = master
        self.board_size = board_size
        self.num_mines = (board_size * board_size) // 5
        self.cell_size = 15
        self.flags_left = self.num_mines
        self.flags = 0
        self.grid()
        self.create_widgets()
        self.create_board()

    def create_widgets(self):
        self.top_frame = tk.Frame(self.master)
        self.top_frame.grid(row=0, column=0, sticky="ew")

        self.restart_button = tk.Button(self.top_frame, text="Restart", command=self.restart_game)
        self.restart_button.pack(side="left")

        self.flags_label = tk.Label(self.top_frame, text=f"Flags left: {self.flags_left}")
        self.flags_label.pack(side="right")

        self.zoom_in_button = tk.Button(self.top_frame, text="Zoom In", command=self.zoom_in)
        self.zoom_in_button.pack(side="left")

        self.zoom_out_button = tk.Button(self.top_frame, text="Zoom Out", command=self.zoom_out)
        self.zoom_out_button.pack(side="left")

        self.canvas_frame = tk.Frame(self.master)
        self.canvas_frame.grid(row=1, column=0, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.canvas_frame, width=self.board_size * self.cell_size, height=self.board_size * self.cell_size)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.v_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self.on_shift_mouse_wheel)
        self.canvas.bind("<Button-2>", self.start_drag)
        self.canvas.bind("<B2-Motion>", self.on_middle_scroll)
        self.master.bind("<Control-MouseWheel>", self.on_ctrl_mouse_wheel)

    def on_canvas_configure(self, event):
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def create_board(self):
        self.board = np.zeros((self.board_size, self.board_size), dtype=int)
        mines = random.sample(range(self.board_size * self.board_size), self.num_mines)
        for mine in mines:
            row, col = divmod(mine, self.board_size)
            self.board[row][col] = -1
            for i in range(max(0, row-1), min(self.board_size, row+2)):
                for j in range(max(0, col-1), min(self.board_size, col+2)):
                    if self.board[i][j] != -1:
                        self.board[i][j] += 1
        self.draw_board()

    def create_board_thread(self):
        thread = threading.Thread(target=self.create_board)
        thread.start()

    def draw_board(self):
        canvas_width = int(self.canvas.cget("width"))
        canvas_height = int(self.canvas.cget("height"))
        for i in range(self.board_size):
            for j in range(self.board_size):
                x1 = j * self.cell_size
                y1 = i * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                if not (x2 < 0 or x1 > canvas_width or y2 < 0 or y1 > canvas_height):
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="gray", outline="black", tags=f"cell_{i}_{j}")

    def is_visible(self, x1, y1, x2, y2):
        canvas_width = int(self.canvas.cget("width"))
        canvas_height = int(self.canvas.cget("height"))
        return not (x2 < 0 or x1 > canvas_width or y2 < 0 or y1 > canvas_height)
    
    def on_left_click(self, event):
        col = int(self.canvas.canvasx(event.x) // self.cell_size)
        row = int(self.canvas.canvasy(event.y) // self.cell_size)
        if row < 0 or row >= self.board_size or col < 0 or col >= self.board_size:
            return
        if "flagged" in str(self.canvas.gettags(f"cell_{row}_{col}")):
            return
        if self.board[row][col] == -1:
            self.canvas.create_text(col * self.cell_size + self.cell_size // 2,
                                    row * self.cell_size + self.cell_size // 2,
                                    text='*', fill='red')
            self.game_over()
        else:
            self.reveal_cells(row, col)

    def on_right_click(self, event):
        col = int(self.canvas.canvasx(event.x) // self.cell_size)
        row = int(self.canvas.canvasy(event.y) // self.cell_size)
        if row < 0 or row >= self.board_size or col < 0 or col >= self.board_size:
            return
        items = self.canvas.find_withtag(f"flag_{row}_{col}")
        if items:
            for item in items:
                if "revealed" in str(self.canvas.gettags(item)):
                    return  # Do not allow flagging revealed cells
                else:
                    # Remove flag by deleting the text item and removing the "flagged" tag
                    self.canvas.delete(item)
                    cell_tags = list(self.canvas.gettags(f"cell_{row}_{col}"))
                    cell_tags.remove("flagged")
                    self.canvas.itemconfig(f"cell_{row}_{col}", tags=tuple(cell_tags))
                    if self.board[row][col] == -1:
                        self.flags -= 1
                    # Increase the flags left count and update the label
                    self.flags_left += 1
                    self.flags_label.config(text=f"Flags left: {self.flags_left}")
        else:
            if "revealed" not in str(self.canvas.gettags(f"cell_{row}_{col}")) and self.flags_left > 0:
                x_center = col * self.cell_size + (self.cell_size // 2)
                y_center = row * self.cell_size + (self.cell_size // 2)
                flag_id = f"flag_{row}_{col}"
                # Add flag by creating a new text item and adding the "flagged" tag
                self.canvas.create_text(x_center, y_center, text='F', fill='yellow', tags=(flag_id,))
                cell_tags = list(self.canvas.gettags(f"cell_{row}_{col}"))
                cell_tags.append("flagged")
                self.canvas.itemconfig(f"cell_{row}_{col}", tags=tuple(cell_tags))
                if self.board[row][col] == -1:
                    self.flags += 1
                # Decrease the flags left count and update the label
                self.flags_left -= 1
                self.flags_label.config(text=f"Flags left: {self.flags_left}")

        # Check all cells to see if they should glow green immediately after flagging/unflagging
        self.update_glow()

        # Check if the player has won
        self.check_win()

    def reveal_cells(self, row, col):
        stack = [(row, col)]
        revealed_cells = set()
        while stack:
            r, c = stack.pop()
            if r < 0 or r >= self.board_size or c < 0 or c >= self.board_size or (r, c) in revealed_cells:
                continue
            revealed_cells.add((r, c))
            items = self.canvas.find_withtag(f"cell_{r}_{c}")
            if not items or "disabled" in str(self.canvas.gettags(items[0])):
                continue

            text_color = 'black' if self.board[r][c] != 0 else 'white'
            text_value = '' if text_color == 'white' else str(self.board[r][c])
            x_center = c * self.cell_size + (self.cell_size // 2)
            y_center = r * self.cell_size + (self.cell_size // 2)
            cell_id = f"cell_{r}_{c}"
            
            fill_color = 'lightgray' if text_color == 'white' else 'gray'
            
            if text_value:
                self.canvas.create_text(x_center, y_center, text=text_value, fill=text_color)
            
            tags = list(self.canvas.gettags(cell_id))
            tags.append("disabled")
            tags.append("revealed")
            self.canvas.itemconfig(cell_id, fill=fill_color, tags=tuple(tags))

            if self.board[r][c] == 0:
                for i in range(max(0, r-1), min(self.board_size, r+2)):
                    for j in range(max(0, c-1), min(self.board_size, c+2)):
                        if (i != r or j != c) and "disabled" not in str(self.canvas.gettags(f"cell_{i}_{j}")):
                            stack.append((i, j))

        self.update_glow()

    def update_glow(self):
        for row in range(self.board_size):
            for col in range(self.board_size):
                if self.board[row][col] > 0 and "revealed" in str(self.canvas.gettags(f"cell_{row}_{col}")):
                    flagged_count = 0
                    for i in range(max(0, row-1), min(self.board_size, row+2)):
                        for j in range(max(0, col-1), min(self.board_size, col+2)):
                            if "flagged" in str(self.canvas.gettags(f"cell_{i}_{j}")):
                                flagged_count += 1
                    cell_id = f"cell_{row}_{col}"
                    if flagged_count == self.board[row][col]:
                        self.canvas.itemconfig(cell_id, fill="green")
                    else:
                        fill_color = 'lightgray' if self.board[row][col] == 0 else 'gray'
                        self.canvas.itemconfig(cell_id, fill=fill_color)

    def check_win(self):
        for i in range(self.board_size):
            for j in range(self.board_size):
                if self.board[i][j] == -1 and not self.canvas.find_withtag(f"flag_{i}_{j}"):
                    return
        if messagebox.askyesno("Minesweeper", "Congratulations! You won! Do you want to restart?"):
            self.restart_game()
        else:
            self.master.destroy()

    def game_over(self):
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<Button-3>")
        for i in range(self.board_size):
            for j in range(self.board_size):
                if self.board[i][j] == -1:
                    self.canvas.create_text(j * self.cell_size + self.cell_size // 2,
                                            i * self.cell_size + self.cell_size // 2,
                                            text='*', fill='red')
                self.canvas.itemconfig(f"cell_{i}_{j}", tags=("disabled",))
        if messagebox.askyesno("Minesweeper", "You clicked on a mine! You lose. Do you want to restart?"):
            self.restart_game()
        else:
            self.master.destroy()

    def restart_game(self):
        self.canvas.delete("all")
        self.create_board_thread()
        self.flags_left = self.num_mines
        self.flags_label.config(text=f"Flags left: {self.flags_left}")
        self.flags = 0
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

    def zoom_in(self):
        self.cell_size += 5
        self.redraw_board()

    def zoom_out(self):
        if self.cell_size > 5:
            self.cell_size -= 5
            self.redraw_board()

    def redraw_board(self):
        revealed_cells = []
        flagged_cells = []
        glowing_cells = []

        for i in range(self.board_size):
            for j in range(self.board_size):
                if "revealed" in self.canvas.gettags(f"cell_{i}_{j}"):
                    revealed_cells.append((i, j))
                if "flagged" in self.canvas.gettags(f"cell_{i}_{j}"):
                    flagged_cells.append((i, j))
                if self.canvas.itemcget(f"cell_{i}_{j}", "fill") == "green":
                    glowing_cells.append((i, j))

        self.canvas.delete("all")
        self.draw_board()

        for row, col in revealed_cells:
            self.reveal_cell(row, col)

        for row, col in flagged_cells:
            self.flag_cell(row, col)

        for row, col in glowing_cells:
            cell_id = f"cell_{row}_{col}"
            self.canvas.itemconfig(cell_id, fill="green")

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def flag_cell(self, row, col):
        x_center = col * self.cell_size + (self.cell_size // 2)
        y_center = row * self.cell_size + (self.cell_size // 2)
        flag_id = f"flag_{row}_{col}"
        self.canvas.create_text(x_center, y_center, text='F', fill='yellow', tags=(flag_id,))
        cell_tags = list(self.canvas.gettags(f"cell_{row}_{col}"))
        cell_tags.append("flagged")
        self.canvas.itemconfig(f"cell_{row}_{col}", tags=tuple(cell_tags))
    
    def reveal_cell(self, row, col):
        text_color = 'black' if self.board[row][col] != 0 else 'white'
        text_value = '' if text_color == 'white' else str(self.board[row][col])
        x_center = col * self.cell_size + (self.cell_size // 2)
        y_center = row * self.cell_size + (self.cell_size // 2)
        cell_id = f"cell_{row}_{col}"
        
        fill_color = 'lightgray' if text_color == 'white' else 'gray'
        
        if text_value:
            self.canvas.create_text(x_center, y_center, text=text_value, fill=text_color)
        
        tags = list(self.canvas.gettags(cell_id))
        tags.append("disabled")
        tags.append("revealed")
        self.canvas.itemconfig(cell_id, fill=fill_color, tags=tuple(tags))

    def on_mouse_wheel(self, event):
        # Scroll vertically
        if event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        else:
            self.canvas.yview_scroll(1, "units")

    def on_shift_mouse_wheel(self, event):
        # Scroll horizontally
        if event.delta > 0:
            self.canvas.xview_scroll(-1, "units")
        else:
            self.canvas.xview_scroll(1, "units")

    def start_drag(self, event):
        # Record the starting position
        self.canvas.scan_mark(event.x, event.y)

    def on_middle_scroll(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_ctrl_mouse_wheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    board_size = simpledialog.askinteger("Board Size", "Enter the board size:", minvalue=5, maxvalue=100)
    
    if board_size:
        root.deiconify()  # Show the main window
        root.title("Minesweeper")
        
        window_size = board_size * 15 + 50
        root.geometry(f"{window_size-25}x{window_size}")  # Set dynamic window size
        
        # Configure grid to make the top frame fixed
        root.grid_rowconfigure(0, weight=0)
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        game = Minesweeper(root, board_size)
        root.mainloop()