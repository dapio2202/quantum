# Final Project - Cryptography and Quantum Computing

This is my final project for the course. It has two parts that are related to each other. The first one is a prime number generator with a small desktop app, and the second one is a demonstration of Shor's algorithm running on a quantum computer (or a simulator of one) that shows how quantum computing can break RSA encryption. I built them separately but they connect thematically since RSA security depends on prime numbers being hard to factor, and Shor's algorithm is exactly what breaks that assumption.

---

## Big_Prime.py

This script opens a small desktop window where you can generate very large prime numbers. You pick how many bits you want (between 8 and 8192) and how many rounds of testing to run, then hit the button and it finds a prime for you.

The algorithm behind it is Miller-Rabin. The way it works is it takes a random candidate number of the right bit size, checks it against a hardcoded list of small primes first to quickly discard obvious composites, and then runs the probabilistic test. Each round of Miller-Rabin picks a random witness and checks if the number behaves like a prime should. If it passes all the rounds it is considered a probable prime. With 40 rounds the probability of a composite slipping through is astronomically small (below 4^-40) so in practice it is fine for cryptographic use.

I used Python's `secrets` module for the random number generation instead of the normal `random` module because `secrets` is cryptographically secure, which matters here since we are generating numbers meant to be used in crypto contexts.

The UI runs the search in a background thread so the window does not freeze while it is working.

To run it:

```bash
python Big_Prime.py
```

No external libraries needed, everything is from the standard library (tkinter, secrets, threading).

---

## real_quantum.py

This one is more complex. It demonstrates Shor's algorithm, which is a quantum algorithm that can factor large integers efficiently. The reason this matters for cryptography is that RSA encryption relies on the fact that factoring a large number into its primes is computationally hard classically. Shor's algorithm does it in polynomial time on a quantum computer, which would make RSA broken if we ever have a big enough quantum computer.

For this project I kept the numbers small (N=15, which factors into 3 and 5) because that is the scale that actually fits on a real quantum device or a reasonable simulator. The script does the following:

1. Builds a toy RSA key from two small primes and encrypts a word with it
2. Runs a quantum phase estimation circuit to find the order of 2 mod 15, meaning the smallest r such that 2^r = 1 mod 15
3. Uses the order to compute gcd(a^(r/2) +/- 1, N) classically, which gives the factors
4. Reconstructs the private RSA key from those factors and decrypts the ciphertext

The quantum part uses Qiskit. The circuit has a control register for the phase estimation and a target register that holds the state being multiplied. The multiplication gates (M2mod15 and M4mod15) are implemented as SWAP sequences since multiplying by 2 mod 15 on 4 qubits is just a cyclic bit shift. After the controlled unitaries the inverse QFT is applied to the control register to read out the phase, and from there continued fractions are used classically to find the order.

You can run it in three modes by changing the `BACKEND_MODE` variable at the top of the file:

| Mode | What it does |
|------|-------------|
| `ideal` | Runs on a local noiseless simulator, fastest option |
| `noisy` | Runs on a local simulator but copies the noise model from a real IBM backend |
| `hardware` | Submits the job to an actual IBM quantum computer |

To install the dependencies:

```bash
pip install qiskit qiskit-ibm-runtime qiskit-aer
```

To run it:

```bash
python real_quantum.py
```

If you want to use `noisy` or `hardware` mode you need an IBM Quantum account. After making one at quantum.ibm.com, save your credentials once like this:

```python
from qiskit_ibm_runtime import QiskitRuntimeService

QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform",
    token="YOUR_API_KEY",
    instance="YOUR_INSTANCE_CRN",
    set_as_default=True,
    overwrite=True,
)
```

You can check it worked by running:

```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()
print([b.name for b in service.backends(operational=True, simulator=False)])
```

It should print a list of available backends like `['ibm_kingston', 'ibm_marrakesh', 'ibm_fez']`.

---

## Requirements

| File | Python version | Libraries |
|------|---------------|-----------|
| Big_Prime.py | 3.10+ | none |
| real_quantum.py | 3.10+ | qiskit, qiskit-ibm-runtime, qiskit-aer |
