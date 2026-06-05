"""
How to run this Python file:

    python Big_Prime.py
"""

import queue
import secrets
import threading
import time
import tkinter as tk
from tkinter import ttk



# This is the firsts primes

_SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 
    239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 
    331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 
    421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 
    509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607, 
    613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 
    709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 
    821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 
    919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997 ]


def miller_rabin(n: int, rounds: int = 40) -> bool:
    if n < 2: # Rejects very small numbers
        return False
    if n < 4:
        return True
    if n % 2 == 0:  # Rejects even numbers
        return False
    s, d = 0, n - 1
    while d % 2 == 0: # It devides by two until its an odd integer
        s += 1
        d //= 2
    for _ in range(rounds): # This gives more confidance for every round
        a = secrets.SystemRandom().randint(2, n - 2) # Random number bigger then 2 and smaller then n - 1 uses this because cryptographically secure
        x = pow(a, d, n)
        if x == 1 or x == n - 1: # If true → passes this round
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False # detects if composite this means definitely NOT prime
    return True # velives that is prime so marked as "Probably prime"


def is_probable_prime(n: int, rounds: int = 40) -> bool:
    if n < 2:
        return False
    for p in _SMALL_PRIMES: # Check for small prime numbers
        if n == p:
            return True
        if n % p == 0:
            return False
    return miller_rabin(n, rounds) # Uses the function that is writen higger then here



class PrimeGenApp: # This is what we use to show the UI
    POLL_MS = 80

    def __init__(self, root: tk.Tk): 
        #This is the base, we definde the size and everything in it
        self.root = root
        root.title("Prime generator")
        root.geometry("600x480")
        root.minsize(420, 360)

        self.msg_queue: "queue.Queue[tuple]" = queue.Queue() # thread communication
        self.current_prime: int | None = None # Store current prime
        self.worker: threading.Thread | None = None # Worker thread

        self._build_ui()
        self._poll_queue()

    # The layout that will show on the UI
    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=16)
        frm.pack(fill="both", expand=True) # expands horizontally + vertically

        # Here we create the inputs
        inputs = ttk.Frame(frm)
        inputs.pack(fill="x", pady=(0, 12)) # A sub-container just for input fields
        inputs.columnconfigure(0, weight=1) # The first input
        inputs.columnconfigure(1, weight=1)# The second input 

        #Bits side
        label_bits = ttk.Label(inputs, text="Bits") # Bits text 
        label_bits.grid(row=0, column=0, sticky="w")
        self.bits_var = tk.StringVar(value="1024") # Initial text inside the text box 1024
        entry_bits = ttk.Entry(inputs, textvariable=self.bits_var)
        entry_bits.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))


        #Rounds side
        label_round = ttk.Label(inputs, text="Rounds") # Rounds text 
        label_round.grid(row=0, column=1, sticky="w")
        self.rounds_var = tk.StringVar(value="40") # Initial text inside the text box 40 
        entry_round = ttk.Entry(inputs, textvariable=self.rounds_var)
        entry_round.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(2, 0))
    
        #error handler
        self.status_var = tk.StringVar(value="")
        self.status_lbl = ttk.Label(frm, textvariable=self.status_var, foreground="gray")
        self.status_lbl.pack(fill="x", pady=(0, 6))


        self.gen_btn = ttk.Button(frm, text="Generate prime", command=self.on_generate) # Creates button and uses function on_generate
        self.gen_btn.pack(fill="x", pady=(0, 10))

        result_box = ttk.Frame(frm, relief="solid", borderwidth=1, padding=10) # Here is where the primer number will apear
        result_box.pack(fill="both", expand=True)

        meta_row = ttk.Frame(result_box)
        meta_row.pack(fill="x", pady=(0, 6))
        self.meta_var = tk.StringVar(value="No prime generated yet.") # It's set to No prime generated yet
        ttk.Label(meta_row, textvariable=self.meta_var, foreground="gray").pack(side="left")

        self.text = tk.Text(
            result_box, wrap="char", height=8, font="TkFixedFont",
            relief="flat", background=self.root.cget("bg"), # Matches backgorund color
        )
        self.text.pack(fill="both", expand=True) # Resizes with window
        self.text.configure(state="disabled") # User can't modify the prime 

    # This is what happens when "Generate prime" button is clicked
    def on_generate(self):
        if self.worker and self.worker.is_alive():
            return # prevents multiple threads
        self._set_status("")

        try:
            bits = int(self.bits_var.get()) # Reads text from bits text box
            rounds = int(self.rounds_var.get()) # Reads text from round text box
        

        except ValueError: # If textbox empty
            self._set_status("Bits and rounds must be integers.", error=True)
            return
        if not (8 <= bits <= 8192): # To control the bits to be betwen 8 and 8192
            self._set_status("Bits must be between 8 and 8192.", error=True)
            return
        if not (1 <= rounds <= 128): # To control rounds arent to high
            self._set_status("Rounds must be between 1 and 128.", error=True)
            return

        self.gen_btn.configure(state="disabled")  # Disable button while searching

        self.worker = threading.Thread(
            target=self._worker, args=(bits, rounds), daemon=True
        )
        self.worker.start()


    def _worker(self, bits: int, rounds: int):
        t0 = time.time() # Starter time
        attempts = 0
        try:
            while True:
                attempts += 1
                n = secrets.randbits(bits) + (1 << (bits - 1)) + 1 # Generates a number from the bits size stablished, and ensures that the first one is a 1, that makes the number big and forces an odd number
                if is_probable_prime(n, rounds): # Ths revises if its a prime number
                    elapsed = time.time() - t0 #calculates the time
                    self.msg_queue.put(("done", (n, attempts, elapsed, bits, rounds))) # Puts a message with time, attemps, bits and rounds
                    return
        except Exception as exc:      # surface unexpected errors to the UI
            self.msg_queue.put(("error", str(exc)))

    def _poll_queue(self): # Runs in repeat in the GUI thread
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait() # It reads a message without blocking
                if kind == "progress":
                    pass
                elif kind == "done": # What happends once is done
                    prime, attempts, elapsed, bits, rounds = payload # Extract all the informacion form the payload
                    self.current_prime = prime # Display the prime

                    self.meta_var.set( # Send the remaning info or display
                        f"{bits}-bit · {attempts} attempts· " 
                        f"{elapsed:.2f}s · {rounds} rounds"
                    )
                    self._set_result_text(str(prime)) # Displays the generated prime in the text box
                    self.gen_btn.configure(state="normal")  # Re-enable button when done
        except queue.Empty:
            pass
        self.root.after(self.POLL_MS, self._poll_queue)

    # Config of the result text box
    def _set_result_text(self, text: str): # Configuration of the text 
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")   
        self.text.insert("1.0", text)
        self.text.configure(state="disabled")
    
    def _set_status(self, message: str, error: bool = False):
        if error:
            colour = "red" 
        else:
            colour = "gray"
        self.status_var.set(message)
        self.status_lbl.configure(foreground=colour)



def main():
    root = tk.Tk() #generate the UI
    PrimeGenApp(root) # Adds everything to the app
    root.mainloop() # starts the UI


if __name__ == "__main__":
    main() #starts the program
