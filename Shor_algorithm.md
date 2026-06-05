
# Full Code Explanation: RSA + Shor's Algorithm

## Table of Contents

1.  Imports and Dependencies
2.  User Configuration
3.  The ToyRSA Dataclass
4.  RSA Key Generation — `build_toy_rsa`
5.  RSA Encryption and Decryption of Integers
6.  Text Encoding: Letters ↔ Numbers
7.  Word-Level Encryption and Decryption
8.  Shor's Algorithm — Modular Exponentiation Helper
9.  Quantum Gates using M2mod15 and M4mod15
10.  Building the Quantum Circuit using`build_order_finding_circuit_N15_a2`
11.  Running the Quantum Simulation using `run_order_finding`
12.  Extracting Order Candidates using `extract_order_candidates`
13.  Recovering Factors using `factors_from_order`
14.  The Main Program — Putting It All Together
15.  Big Picture: How Everything Connects

----------

## 1. Imports and Dependencies

```python
from dataclasses import dataclass
from fractions import Fraction
from math import gcd

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import QFT
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_aer import AerSimulator
```

### Standard Library

-   **`dataclass`**: This is what we use to define the dataclass `ToyRSA`.
-   **`Fraction`**: We will use this to extract a rational number (fraction) from the period `r` so we are able to show it in console as a result.
-   **`gcd`**: This allows us to compute the GCD.

### Qiskit (Quantum Computing Library)

-   **`QuantumCircuit`**: The main object representing a quantum program. You add gates to it step by step.
-   **`QuantumRegister`**: This allows us to use qubits (quantum bits).
-   **`ClassicalRegister`**: These are bits used to store the results when measuring the qubits.
-   **`QFT`**: Allows us to use one pillar named the Quantum Fourier Transform that will allow us to break RSA.
-   **`generate_preset_pass_manager`**: This is what transcribes (compiles) our abstract circuit into the native gate set and qubit topology of whatever backend we are using. Without it, we would need to type on the native lenguage.
-   **`QiskitRuntimeService`**: This is the client that connects to IBM Quantum Platform so we can submit jobs to real quantum processors.
-   **`SamplerV2 as Sampler`**: This is the runtime primitive that actually runs the circuit on the selected backend (whether local or real hardware) and returns the measurement counts.
-   **`AerSimulator`**: This is the local quantum simulator. We use it in two ways: as a noiseless simulator to verify the algorithm, and loaded with a real backend's noise model to preview hardware behaviour without using our IBM quota.
----------

## 2. User Configuration

This are our initial values:

```python
P = 3       # prime factor
Q = 5       # prime factor
E = 3       # public exponent
PLAINTEXT_WORD = "HELLO"
NUM_CONTROL_QUBITS = 5
SHOTS = 2048
SEED = 42
BACKEND_MODE = "ideal"   # "ideal" | "noisy" | "hardware"
```

-   **P and Q**: These two prime numbers are the product that will produce the **toy RSA** modulus N. In a real case scenario, these numbers would be extremely big, they would have 2048 bits instead of just 4. So in this example we will use 3 and 5 to have an N of 15
-   **E**: This is the public exponent used for encryption. Just to remember, this number has to be a coprime of `phi(N)`, and also has to be smaller than N, so in this case we will use the number 3, but in real RSA we normally use 65537 because it is standard
-   **PLAINTEXT_WORD**: This is the secret message that we want to send.
-   **NUM_CONTROL_QUBITS**: Controls how precise it will be during the quantum phase estimation. More qubits → more precise phase → better chance of finding the correct order `r`. 5 qubits gives 2^5 = 32 possible measurement outcomes, which is enough precision for r=4 and keeps the circuit shallow enough to run cleanly on real hardware.
-   **SHOTS**: The amout of times the quantum circuit is simulated and measured. More shots give more statistically reliable results but then makes all the machine slower.
-   **SEED**: Fixes the random number generator for reproducibility to ensure that everything works.
-   **BACKEND_MODE**: Selects where the circuit runs. `"ideal"` uses a noiseless local Aer simulator (fast and free), `"noisy"` uses a local Aer simulator initialised with the noise model of a real IBM processor (more realistic run and faster then real hardware), and `"hardware"` submits the job to a real IBM Quantum processor through the free Open Plan.

----------
## 3. The ToyRSA Dataclass
```python
@dataclass
class ToyRSA:
    p: int
    q: int
    N: int
    phi: int
    e: int
    d: int
```
This is a simple data container holding all the components of an RSA key pair, and those are the meaning:
`p`: First prime factor
`q`: Second prime factor
`N`: Public modulus: `p * q`
`phi`: Euler's totient: `(p-1) * (q-1)`
`e`: Public exponent coprime of `phi` (part of public key)
`d`: Private exponent (part of private key)

The **public key** (the key that you will share) is the pair `(e, N)`, anyone can use it to encrypt messages.  
The **private key** (the key that you will keep secret) is the pair `(d, N)`, only the owner can use it to decrypt the message.

----------
## 4. RSA Key Generation — `build_toy_rsa`

```python
def build_toy_rsa(p: int, q: int, e: int) -> ToyRSA:
    N = p * q
    phi = (p - 1) * (q - 1)

    if gcd(e, phi) != 1:
        raise ValueError(f"e={e} is not coprime with phi={phi}")

    d = pow(e, -1, phi)
    return ToyRSA(p=p, q=q, N=N, phi=phi, e=e, d=d)
```

### Step-by-step:
**Step 1 is to compute N by multiplying both prime numbers:**
```
N = p * q = 3 * 5 = 15
```
N is the modulus. All encryption and decryption operations are done "mod N". In our case is `N=15`

**Step 2 is to compute phi(N):**
```
phi(N) = (p - 1) * (q - 1) = 2 * 4 = 8
```
Euler's totient function `phi(N)` this is the amout of integers from 1 to N are coprime with N. This number is the "order" of the multiplicative group mod N, and it's what makes RSA tick. To create `phi(N)` you have to subtract 1 from both prime numbers and then multiply them to each other.

**Step 3 we have to chose e:** Here we validate that e is coprime with `phi` by doing `gcd(e, phi)`, coprime means that e and phi share no common factors other than 1.

**Step 4 finally we have to compute d:**
```python
d = pow(e, -1, phi)
```
Using python's `pow(e, -1, phi)` we are able to compute the **modular multiplicative inverse** of e modulo phi, and be able to get the variable `d`. This means:
```
e * d ≡ 1 (mod phi)
3 * d ≡ 1 (mod 8)  →  d = 3  (because 3*3 = 9 = 8+1 ≡ 1 mod 8)
```
This is done to get the important part of the private key `d`, and this way you would be able to retrieve the initial message by decrypting the message that we received.

----------

## 5. RSA Encryption and Decryption of Integers

```python
def encrypt_int(m: int, rsa: ToyRSA) -> int:
    if not (0 <= m < rsa.N):
        raise ValueError(...)
    return pow(m, rsa.e, rsa.N)

def decrypt_int(c: int, rsa: ToyRSA) -> int:
    return pow(c, rsa.d, rsa.N)
```

### Encryption:
```
C = M^e mod N
```
For example, if we would like to encrypt the letter 'H' (this would be the letter number 7) would be done the following way:
```
C = 7^3 mod 15 = 343 mod 15 = 13
```
### Decryption:
```
M = C^d mod N
```
And if we would like to decrypt the message earlier encrypted, the number 13 with d=3 we would do it this way to retrieve the initial message:
```
M = 13^3 mod 15 = 2197 mod 15 = 7  → back to 'H' ✓
```
----------
## 6. Text Encoding: Letters ↔ Numbers
Because RSA only works on integers, not characters, we need a function that transforms from letters to numbers. This is that function.
```python
def normalize_word(word: str) -> str:
    return word.replace(" ", "")
```
First of all we remove the spaces from the secret word so only alphabetic characters remain, and also all the letters are put in upper case, this is done to minimize the errors.

----------
```python
def char_to_number(ch: str, N: int) -> int:
    value = ord(ch.upper()) - ord("A")
    if value >= N:
        raise ValueError(...)
    return value
```
The function `ord()` returns the ASCII code of a character. The example with a is `ord('A') = 65` so what we do is we subtract 65 so the letters start with 0 instead of 65 for a reason that we will explain later, so the letters would be like this:
```
'A' → 0,  'B' → 1,  'C' → 2,  ...,  'H' → 7,  ...,  'Z' → 25
```
The constraint `value < N` is important: since encryption is done mod N, any number ≥ N would produce a collision (two different letters mapping to the same ciphertext). With N=15, only letters A through O (values 0–14) are safe to use.

----------
```python
def number_to_char(n: int) -> str:
    if not (0 <= n <= 25):
        return f"[{n}]"
    return chr(ord("A") + n)
```
This function transforms from a number back into the original letter (used during decrypton):`chr(65 + 7) = 'H'` (remember that here we have to add the 65 that we subtracted earlier). If the number is out of alphabet range, it returns a bracketed fallback.

----------
```python
def word_to_numbers(word: str, N: int) -> list[int]:
    clean = normalize_word(word)
    return [char_to_number(ch, N) for ch in clean]

def numbers_to_word(numbers: list[int]) -> str:
    return "".join(number_to_char(n) for n in numbers)
```
These apply the character conversion to every letter in a word, producing a list of integers (or vice versa). For "HELLO" with N=15:
```
H→7, E→4, L→11, L→11, O→14  →  [7, 4, 11, 11, 14]
```

----------

## 7. Word-Level Encryption and Decryption
```python
def encrypt_word(word: str, rsa: ToyRSA) -> list[int]:
    plaintext_numbers = word_to_numbers(word, rsa.N)
    return [encrypt_int(m, rsa) for m in plaintext_numbers]

def decrypt_word(cipher_blocks: list[int], rsa: ToyRSA) -> str:
    plaintext_numbers = [decrypt_int(c, rsa) for c in cipher_blocks]
    return numbers_to_word(plaintext_numbers)
```

As already mentioned, this is not the **real RSA**: in our code, each character is encrypted one by one **independently** , using the public key. In real-world RSA this can lead to problems because if you woud to indetify one characters would leak information about the message easily because they would be able to decrypt all the equal symbols. So, the solution that was found was that in real implementations we use **RSA-OAEP** to ensure that every letter is encrypted in a different way, but for our educational demo, the simple version suffices.

Our secret key will be "HELLO":
```
Encrypt: [7,4,11,11,14] → [13, 4, 11, 11, 14]   (H→13, E→4, L→11 unchanged, O→14)
Decrypt: [13,4,11,11,14] → [7,4,11,11,14] → "HELLO"
```

----------

## 8. Shor's Algorithm — Modular Exponentiation Helper

Here is where we start with the preparation for quantum computing:
```python
def a2kmodN(a: int, k: int, N: int) -> int:
    for _ in range(k):
        a = pow(a, 2, N)
    return a
```
This first function computes `a^(2^k) mod N` by repeatedly squaring a to `2^k` and that `k` is an incremental value. For example, with a=2, N=15:
```
k=0: 2^(2^0) = 2^1 = 2    mod 15 = 2
k=1: 2^(2^1) = 2^2 = 4    mod 15 = 4
k=2: 2^(2^2) = 2^4 = 16   mod 15 = 1
k=3: 2^(2^3) = 2^8 = 256  mod 15 = 1
...
```
This precomputes which controlled gate to apply for each control qubit in the quantum circuit.

----------
## 9. Quantum Gates: M2mod15 and M4mod15

These functions build quantum circuits that implement modular multiplication.
```python
def M2mod15():
    qc = QuantumCircuit(4, name="M2mod15")
    qc.swap(2, 3)
    qc.swap(1, 2)
    qc.swap(0, 1)
    return qc.to_gate(label="M2")
```
### What is a SWAP gate?
What a SWAP gate does is exchange the states of two qubits. In this example the target register holds a 4-qubit number in binary. Doing these swap gates and applying three swaps in sequence shifts all bits one position to the left, which is equivalent to multiplying by 2.
For example, if the target holds `|0001⟩` (= 1), after using the function M2mod15 and doing a swap on the two rightmost qubits this is what it becomes `|0010⟩` (= 2):
```
|q3 q2 q1 q0⟩ = |0 0 0 1⟩ → swap(0,1) → |0 0 1 0⟩ → swap(1,2) → |0 1 0 0⟩... 
```
The other function does the same but multiplying by 4 instead of 2.
```python
def M4mod15():
    qc = QuantumCircuit(4, name="M4mod15")
    qc.swap(1, 3)
    qc.swap(0, 2)
    return qc.to_gate(label="M4")
```
Two swaps implement `×4 mod 15` (a 2-bit left-shift in the 4-qubit register).
These are **hand-crafted** for N=15 and a=2. A general Shor implementation would require a more complex construction, but is enough for this example.

----------

## 10. Building the Quantum Circuit — `build_order_finding_circuit_N15_a2`

```python
def build_order_finding_circuit_N15_a2(num_control: int = 8) -> QuantumCircuit:
    N = 15
    a = 2
    num_target = 4

    control = QuantumRegister(num_control, "control")
    target  = QuantumRegister(num_target, "target")
    out     = ClassicalRegister(num_control, "out")

    qc = QuantumCircuit(control, target, out)
```
### Register layout:
-   **control register** (5 qubits): These will be put into superposition so it can be used to control the modular multiplications. After the using the inverse QFT, measuring them gives us phase information and if everything worked as intended we will be able to find the period. 
-   **target register** (4 qubits): Holds the running value of `a^x mod N`. It starts at `|1⟩`.
-   **out** (5 classical bits): Stores the measurement results of the control qubits.
----------
```python
    qc.x(target[0])
```
Initializes a qubit so we get the following combinaiton `|0001⟩` = 1 because right now we had the qubits in that way `|0000⟩` = 0, so we have to use the X gate (Pauli-X) to flip from a  `|0⟩` to a `|1⟩`. This is the `|1⟩` state that will be multiplied by `a^x` during the circuit so we can do the repetition and find the `r`.

----------
```python
    for k, ctrl_qubit in enumerate(control):
        qc.h(ctrl_qubit)
        b = a2kmodN(a, k, N)

        if b == 2:
            qc.append(M2mod15().control(), [ctrl_qubit] + list(target))
        elif b == 4:
            qc.append(M4mod15().control(), [ctrl_qubit] + list(target))
        else:
            pass
```
### What happens in this loop?
**For each control qubit k:**
1.  **Hadamard gate `H`**: First of all we use a Hadamard gate on all the qubits so puts them into superposition: `|0⟩ → (|0⟩ + |1⟩)/√2`(this means that all the qubits have a 50% chance of being a 0 and a 50% chance of being a 1). After applying H to all control qubits, the control register is in a uniform superposition of all numbers 0 to 2^5 - 1 simultaneously. This is the quantum parallelism step.
    
2.  **Precompute b = a^ 
(2^k) mod N**: This function tells us which gate we have to apply, either `M2mod15` or `M4mod15`. For a=2, N=15:
    -   k=0: b=2 → apply M2 (×2 mod 15)
    -   k=1: b=4 → apply M4 (×4 mod 15)
    -   k=2: b=1 → do nothing (×1 = identity)
    -   k≥2: b=1 → do nothing (2^4=16≡1 mod 15, so all higher powers are also 1)
3.  **Controlled gate**: The `.control()` method wraps a gate so it only applies when the control qubit is in state `|1⟩`. This implements the **controlled modular multiplication** `|ctrl⟩|x⟩ → |ctrl⟩|a^ctrl * x mod N⟩`.
    
The combined effect across all control qubits creates the quantum state:
```
(1/√2^n) * Σ_k |k⟩|a^k mod N⟩
```
Which encodes the entire sequence of powers `a^0, a^1, a^2, ...` simultaneously by using the power of superposition.

----------

```python
    qc.compose(QFT(num_control, inverse=True), qubits=control, inplace=True)
    qc.measure(control, out)
```

**Inverse QFT**: The Quantum Fourier Transform converts between the exponent k and the phase. Then the inverse QFT is applied to the control register, which transforms the superposition into peaks at multiples of `2^(n/r)`, so we are able to find `r` in order to find that repetition and find the order we are looking for. This is the heart of Shor's algorithm.

**Measurement**: What this does is collapse the quantum state to analyze the results. Each shot gives one of the peak values. 

----------
## 11. Running the Quantum Simulation — `run_order_finding`

```python
def run_order_finding(qc: QuantumCircuit, sampler, backend, shots: int = 2048):
    pm = generate_preset_pass_manager(backend=backend, optimization_level=3)
    isa_qc = pm.run(qc)

    sampler.options.default_shots = shots
    job = sampler.run([isa_qc])
    result = job.result()[0]
    return result.data.out.get_counts()
```

Before this function runs, the program selects a backend through a helper that reads `BACKEND_MODE` and returns the right sampler and backend objects: a local Aer simulator (noiseless or with a noise model) or a real IBM Quantum processor through `QiskitRuntimeService`.

-   **`generate_preset_pass_manager` + `pm.run(qc)`**: This is the **transpilation** step. Our abstract circuit (with controlled M2mod15, M4mod15 and the QFT) is compiled into the native gate set and qubit topology of the target backend. This is mandatory for real hardware. We use `optimization_level=3` so the transpiler optimises aggressively, which matters a lot because the controlled gates expand into long Toffoli sequences.
-   **`Sampler` (SamplerV2)**: This is the runtime primitive that runs the transpiled circuit on the selected backend. The same primitive is used for all three modes; only the backend object passed to it changes. It uses the parameter  `shots` explained earlier.
-   **`sampler.run([isa_qc])`**: Submits the job on the local simulator this returns in seconds; on real hardware it goes through a queue and may take from seconds to minutes.
-   **`get_counts()`**: Returns the information `{bitstring: count}`, e.g. `{'01000': 512, '10000': 510, ...}`, then the  bitstrings are the mesured and the counts tell how many times each was observed.

----------
## 12. Extracting Order Candidates — `extract_order_candidates`

```python
def extract_order_candidates(counts: dict, num_control: int, N: int = 15):
    for bitstring, count in sorted(counts.items(), ...):
        decimal = int(bitstring, 2)
        phase = decimal / (2 ** num_control)

        frac = Fraction(phase).limit_denominator(N)
        r = frac.denominator
```

### Step-by-step:

**Step 1 — First of all we convert the bitstring into a decimal:**
```
'01000000' → 64  (binary to decimal)
```
**Step 2 — Then we compute the phase:**
```
phase = 64 / 256 = 0.25
```
The QFT has the objective of mapping the order `r` to peaks at positions `k * 2^(n/r)` for integer k. Dividing by `2^n` gives the phase `k/r`.
**Step 3 — We then approximate as a fraction:**
```python
Fraction(0.25).limit_denominator(15) = 1/4
```
The `limit_denominator(N)` function implements a **continued fraction algorithm** that can identify the most accurate rational approximation for a given value, limited by a maximum denominator that we can call N.
**Step 4 — Then we extract the order:**
```
r = frac.denominator = 4
```
This shows that for `a=2, N=15`, the true order is `r=4` because if we do `2^4 = 16 ≡ 1 (mod 15)` so because we come back to 1 it means that is a possible r. We verify: `2^1=2, 2^2=4, 2^3=8, 2^4=16≡1`.

----------
## 13. Recovering Factors — `factors_from_order`
```python
def factors_from_order(a: int, N: int, r: int):
    if r is None or r % 2 != 0:
        return None

    x = pow(a, r // 2, N)

    f1 = gcd(x - 1, N)
    f2 = gcd(x + 1, N)
    ...
```
This is the **classical post-processing** step of Shor's algorithm.
### Why does this work? (The math)
If `r` is the order of `a` mod N, then by definition:
```
a^r ≡ 1 (mod N)
```
Which means:
```
a^r - 1 ≡ 0 (mod N)
(a^(r/2) - 1)(a^(r/2) + 1) ≡ 0 (mod N)
```
If r is even (it must be even or the result won't work), we let `x = a^(r/2) mod N`. Then:
```
(x - 1)(x + 1) ≡ 0 (mod N)
```
If neither factor is itself divisible by N, then `gcd(x-1, N)` and `gcd(x+1, N)` will reveal both prime factors of N and if we find them we are able to recreate the private key and decrypt the message.
### Example with a=2, N=15, r=4:
```
x = 2^(4/2) mod 15 = 2^2 mod 15 = 4

f1 = gcd(4 - 1, 15) = gcd(3, 15) = 3  ← factor!
f2 = gcd(4 + 1, 15) = gcd(5, 15) = 5  ← factor!
```
Here we have the example of how it would look in our code when we recover p=3 and q=5, that are exactly the primes we started with and we were searching.
### Conditions that would make it fail:
-   **r is odd**: Because the factoring trick only works for even r. In that case it would be extremely easy because we would only discard the candidate and then search for another one.
-   **r is None**: The phase was 0, so no order was extracted and it isn't important.
-   `gcd(x±1, N)` equals 1 or N: Sometimes the trivial factor doesn't help, this happens with certain (a, N) combinations and the solution to this issue is to pick another `a`.

----------
## 14. The Main Program — Putting It All Together
```python
def main():
```
This is the main function that orchestrates the entire program, in this case is done in four logical phases:
### Phase 1 — RSA Setup
```python
rsa = build_toy_rsa(P, Q, E)
plaintext_numbers = word_to_numbers(PLAINTEXT_WORD, rsa.N)
ciphertext_blocks = encrypt_word(PLAINTEXT_WORD, rsa)
```
This first phase generates the RSA key pair and encrypts the secret word "HELLO". The output shows all the key generation math, and the steps for the encryption, also the per-character encryption table with verification, and finally the public and private keys.
### Phase 2 — Classical Decryption Check
```python
recovered_classically = decrypt_word(ciphertext_blocks, rsa)
```
In this second phase we ensure that the message can be decrypted using the generated private key `d`. This ensures that the RSA implementation was correct and when we find `r` we will be able to crack the encryption.
### Phase 3 — Shor's Algorithm (Quantum Phase)
```python
qc = build_order_finding_circuit_N15_a2(num_control=NUM_CONTROL_QUBITS)
counts = run_order_finding(qc, sampler, backend, shots=SHOTS)
candidates = extract_order_candidates(counts, num_control=NUM_CONTROL_QUBITS, N=15)
```
This third phase builds and runs the quantum circuit in order to find the initial prime numbers. At the start of the code, the backend is chosen using the variable `BACKEND_MODE` and the circuit is automatically transpiled to match it before being submitted. Then, we print the top measurement results (the bitstrings and their probabilities) and the table of order candidates derived from the phase estimation.
### Phase 4 — Factoring and RSA Cracking
```python
for c in candidates:
    r = c["r"]
    factors = factors_from_order(a=2, N=15, r=r)
    if factors is not None:
        ...
        break

cracked_rsa = build_toy_rsa(p_rec, q_rec, rsa.e)
recovered_word = decrypt_word(ciphertext_blocks, cracked_rsa)
```
This last phase iterates through all candidates until a valid factoring is found. Then when we find the `r` we are able to reconstruct the RSA private key, and from there decrypt the secret message and get it back, the important thing here is that we have done all this without accessing the real private key. This is the "attack" that Shor's algorithm enables.

----------
## 15. Big Picture: How Everything Connects
```
┌─────────────────────────────────────────────────────────────────┐
│                        SETUP                                    │
│  p=3, q=5  →  N=15, phi=8  →  e=3, d=3   (RSA key pair)         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ENCRYPTION                                  │
│  "HELLO" → [7,4,11,11,14] → C = M^3 mod 15 → ciphertext         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
┌─────────────────────┐    ┌───────────────────────────────────┐
│  CLASSICAL DECRYPT  │    │         SHOR'S ATTACK             │
│  M = C^d mod 15     │    │                                   │
│  (uses private d=3) │    │  Quantum: Find order r of 2 mod 15│
│                     │    │    → r=4  (2^4 ≡ 1 mod 15)        │
│  "HELLO" ✓          │    │                                   │
└─────────────────────┘    │  Classical: gcd(2^2 ± 1, 15)      │
                           │    → factors 3 and 5              │
                           │                                   │
                           │  Reconstruct: build_toy_rsa(3,5,3)│
                           │    → cracked d = 3                │
                           │                                   │
                           │  Decrypt: M = C^d mod 15          │
                           │    → "HELLO" ✓ (without knowing d)│
                           └───────────────────────────────────┘
```
