"""
Setup (first time using it, do the following lines in the terminal):

    python

    pip install qiskit qiskit-ibm-runtime qiskit-aer

    from qiskit_ibm_runtime import QiskitRuntimeService

    QiskitRuntimeService.save_account(
        channel="ibm_quantum_platform",
        token="YOUR_44_CHAR_API_KEY",
        instance="YOUR_INSTANCE_CRN",
        set_as_default=True,
        overwrite=True,
    )

    exit()


To check if worked correcly:

    python 

    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService()
    
    print([b.name for b in service.backends(operational=True, simulator=False)]) 

    exit()

    It should give something like: ['ibm_kingston', 'ibm_marrakesh', 'ibm_fez']

"""

from dataclasses import dataclass

from fractions import Fraction
from math import gcd

# IBM Quantum Runtime: cloud-side sampler and service client
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

from qiskit_aer import AerSimulator

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import QFT
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# USER CONFIG

P = 3                   # prime factor
Q = 5                   # prime factor
E = 3                   # public exponent
PLAINTEXT_WORD = "Hello"

NUM_CONTROL_QUBITS = 5

SHOTS = 2048
SEED = 42               # only used in local "ideal" / "noisy" modes

# Where to run the order-finding circuit:
#   ideal    → noiseless local Aer simulator (fast, free, perfect peaks)
#   noisy    → local Aer with a real backend's noise model (preview of HW)
#   hardware → real IBM QPU via Qiskit Runtime (consumes Open Plan minutes)
BACKEND_MODE = "ideal"


# RSA CLASS
@dataclass
class ToyRSA:
    p: int
    q: int
    N: int
    phi: int
    e: int
    d: int


def build_toy_rsa(p: int, q: int, e: int) -> ToyRSA:
    #Generates an RSA key pair from two primes and a public exponent.
    N = p * q
    phi = (p - 1) * (q - 1)

    if gcd(e, phi) != 1:
        raise ValueError(f"e={e} is not coprime with phi={phi}")

    d = pow(e, -1, phi)
    return ToyRSA(p=p, q=q, N=N, phi=phi, e=e, d=d)


def encrypt_int(m: int, rsa: ToyRSA) -> int:
    #Encrypts one integer m using C = m^e mod N.
    if not (0 <= m < rsa.N):
        raise ValueError(f"Message integer must satisfy 0 <= m < N={rsa.N}")
    return pow(m, rsa.e, rsa.N)


def decrypt_int(c: int, rsa: ToyRSA) -> int:
    decrypted_message = pow(c, rsa.d, rsa.N)
    return decrypted_message


def normalize_word(word: str) -> str:
    # Replace all spaces " " with nothing ""
    word_without_spaces = word.replace(" ", "")
    return word_without_spaces


def char_to_number(ch: str, N: int) -> int:
    if len(ch) != 1 or not ch.isalpha():
        raise ValueError("Use a single alphabetic character")
    value = ord(ch.upper()) - ord("A")
    if value >= N:
        raise ValueError(
            f"The character '{ch}' maps to {value}, and it's outside of limits becasye it must be < N={N}. Choose a bigger N or use letters earlier in the alphabet."
        )
    return value


def number_to_char(n: int) -> str:
    if n < 0 or n > 25:
        return f"[{n}]"
    resulting_character = chr(ord("A")+n)
    return resulting_character

def word_to_numbers(word: str, N: int) -> list[int]:
    clean_word = normalize_word(word)
    number_list = []
    
    for ch in clean_word:
        number = char_to_number(ch, N)
        number_list.append(number)
        
    return number_list


def numbers_to_word(numbers: list[int]) -> str:
    word_characters = []    
    for n in numbers:
        word_characters.append(number_to_char(n))
        
    return "".join(word_characters)


def encrypt_word(word: str, rsa: ToyRSA) -> list[int]:
    plaintext_numbers = word_to_numbers(word, rsa.N)
    ciphertext_numbers = []
    
    for m in plaintext_numbers:
        ciphertext_numbers.append(encrypt_int(m, rsa))
        
    return ciphertext_numbers

def decrypt_word(cipher_blocks: list[int], rsa: ToyRSA) -> str:
    decrypted_numbers = []
    
    for c in cipher_blocks:
        decrypted_numbers.append(decrypt_int(c, rsa))
    
    decrypted_word = numbers_to_word(decrypted_numbers)
    return decrypted_word


# Here is where we have the Shor's algorithm quantum circuit


def a2kmodN(a: int, k: int, N: int) -> int:
    #Computes a^(2^k) mod N by repeated squaring.
    for _ in range(k):
        a = pow(a, 2, N)
    return a


def M2mod15():
    #|x⟩ → |2x mod 15⟩ on 4 qubits via bit-shift swaps.
    qc = QuantumCircuit(4, name="M2mod15")
    qc.swap(2, 3) # Swap the fourth to the third qubit
    qc.swap(1, 2) # Swap the third to the second qubit
    qc.swap(0, 1) # Swap the second to the first qubit
    return qc.to_gate(label="M2")


def M4mod15():
    #|x⟩ → |4x mod 15⟩ on 4 qubits.
    qc = QuantumCircuit(4, name="M4mod15")
    qc.swap(1, 3) # Swap the fourth to the second qubit
    qc.swap(0, 2) # Swap the third to the first qubit
    return qc.to_gate(label="M4")


def build_order_finding_circuit_N15_a2(num_control: int = 8) -> QuantumCircuit:
    # Quantum phase estimation circuit for the order of 2 mod 15.
    N = 15
    a = 2
    num_target = 4

    control = QuantumRegister(num_control, "control")
    target = QuantumRegister(num_target, "target")
    out = ClassicalRegister(num_control, "out")

    qc = QuantumCircuit(control, target, out)

    # Prepare target = |0001⟩ (the multiplicative identity)
    qc.x(target[0])

    for k, ctrl_qubit in enumerate(control):
        qc.h(ctrl_qubit)
        b = a2kmodN(a, k, N)

        if b == 2:
            qc.append(M2mod15().control(), [ctrl_qubit] + list(target))
        elif b == 4:
            qc.append(M4mod15().control(), [ctrl_qubit] + list(target))
        else:
            pass  # b == 1: multiplication by 1 is the identity, nothing to do

    qc.compose(QFT(num_control, inverse=True), qubits=control, inplace=True)
    qc.measure(control, out)

    return qc


def get_sampler_and_backend(mode: str, backend_name: str | None = None):
    
    #Here is where we decide what type we want based on the selected mode.

    # This first option is executed when we want no noise and an ideal result 
    if mode == "ideal":
        backend = AerSimulator(seed_simulator=SEED)
        sampler = Sampler(mode=backend)
        lable = "Aer ideal simulator (local, noiseless)"
        return sampler, backend, lable

    # This second option is executed when we want some noise to make the simulation a little bit more realistic 
    if mode == "noisy":
        service = QiskitRuntimeService() #Conection to IBM

        if backend_name:
            real_backend = service.backend(backend_name)
        else:
            real_backend = service.least_busy(operational=True, simulator=False)
        
        backend = AerSimulator.from_backend(real_backend, seed_simulator=SEED) # Dowload blueprint to the simulator
        sampler = Sampler(mode=backend)
        lable = f"Aer with noise model of {real_backend.name} (local)"
        return sampler, backend, lable
    
    # This last option is executed when we want to use real hardware
    if mode == "hardware":
        service = QiskitRuntimeService() #Conection to IBM

        if backend_name:
            backend = service.backend(backend_name)
        else:
            backend = service.least_busy(operational=True, simulator=False)
        
        sampler = Sampler(mode=backend)
        lable = "IBM Quantum hardware:" + backend.name
        return sampler, backend, lable

    raise ValueError(f"Unknown BACKEND_MODE: {mode!r}")


    #This function runs the code after being transcribed
def run_order_finding(qc: QuantumCircuit, sampler, backend, shots: int = 2048):

    pm = generate_preset_pass_manager(backend=backend, optimization_level=3) #Translates from our circuit to what ever backend we are using
    
    isa_qc = pm.run(qc) 

    #sende the shoot and submit to what ever backend you are using
    sampler.options.default_shots = shots #2048 shots
    job = sampler.run([isa_qc])

    print(f"  Waiting for results...")
    result = job.result()[0] # Wait for everything to end
    return result.data.out.get_counts() # Returns raw bits like {'11000': 485, '00100': 12}


# Here we have the classical post-processing


def extract_order_candidates(counts: dict, num_control: int, N: int = 15):
    #Turns measurement bitstrings into candidate orders r via continued fractions.

    candidates = []

    for bitstring, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        decimal = int(bitstring, 2) #Base-10 integer
        phase = decimal / (2 ** num_control) 

        if phase == 0: #If all 0, then is 0
            candidates.append({
                "bitstring": bitstring,
                "count": count,
                "phase": phase,
                "fraction": "0",
                "r": None,
            })
            continue

        frac = Fraction(phase).limit_denominator(N) #Finds clean fraction with denomintor max N
        r = frac.denominator 

        candidates.append({ # Saves the info 
            "bitstring": bitstring,
            "count": count,
            "phase": phase,
            "fraction": f"{frac.numerator}/{frac.denominator}",
            "r": r,
        })

    return candidates


def factors_from_order(a: int, N: int, r: int):
    #Given an order r of a mod N, attempts to recover a non-trivial factor of N.
    if r is None or r % 2 != 0:
        return None

    experimental_r = pow(a, r // 2, N)

    f1 = gcd(experimental_r - 1, N)
    f2 = gcd(experimental_r + 1, N)

    valid = []
    if 1 < f1 < N:
        valid.append(f1)
    if 1 < f2 < N and f2 not in valid:
        valid.append(f2)

    if not valid:
        return None

    if len(valid) == 1:
        return tuple(sorted((valid[0], N // valid[0])))

    return tuple(sorted(valid))



def main():

    print("=" * 60)
    print("RSA SETUP")
    print("=" * 60)

    rsa = build_toy_rsa(P, Q, E)

    plaintext_numbers = word_to_numbers(PLAINTEXT_WORD, rsa.N)
    ciphertext_blocks = encrypt_word(PLAINTEXT_WORD, rsa)

    print()
    print("--- Key Generation ---")
    print(f"  Prime p              = {rsa.p}")
    print(f"  Prime q              = {rsa.q}")
    print(f"  Modulus  N = p*q     = {rsa.N}")
    print(f"  Totient  phi(N)      = (p-1)*(q-1) = {rsa.p-1}*{rsa.q-1} = {rsa.phi}")
    print(f"  Public exponent  e   = {rsa.e}  (coprime with phi: gcd({rsa.e},{rsa.phi}) = {gcd(rsa.e, rsa.phi)})")
    print(f"  Private exponent d   = {rsa.d}  (e*d mod phi = {(rsa.e * rsa.d) % rsa.phi}, must be 1)")
    print()

    print(f"  Public  key: (e={rsa.e},  N={rsa.N})")
    print(f"  Private key: (d={rsa.d}, N={rsa.N})")
    print()

    print("--- Encryption ---")
    print(f"  Plaintext word       = '{PLAINTEXT_WORD}'")
    print(f"  Formula used: C = M^e mod N  =>  M^{rsa.e} mod {rsa.N}")

    print()
    print(f"  {'Char':<6} {'Plaintext M':<14} {'Ciphertext C':<16} {'Verification: C^d mod N'}")
    print(f"  {'-'*69}")
    for ch, m, c in zip(PLAINTEXT_WORD, plaintext_numbers, ciphertext_blocks):
        ver=""
        verify = pow(c, rsa.d, rsa.N)
        if (verify == m):
            ver = "OK"
        else:
            ver="FAIL"
        print(f"  {ch:<6} {m:<14} {c:<16} {verify:<22}  ({ver}) |")
    print(f"  {'-'*69}")

    print()
    print(f"  Plaintext numbers    = {plaintext_numbers}")
    print(f"  Ciphertext blocks    = {ciphertext_blocks}")

    # Final Prints


    print()
    print("=" * 60)
    print("CLASSICAL DECRYPTION CHECK")
    print("=" * 60)

    recovered_classically = decrypt_word(ciphertext_blocks, rsa)
    print()
    print(f"  Formula used: M = C^d mod N  =>  C^{rsa.d} mod {rsa.N}")
    print(f"  Ciphertext blocks    = {ciphertext_blocks}")
    print(f"  Recovered numbers    = {[decrypt_int(c, rsa) for c in ciphertext_blocks]}")
    print(f"  Recovered word       = '{recovered_classically}'")

    if recovered_classically.upper() == PLAINTEXT_WORD.upper():
                aux="YES ✓"
    else:
            aux = "No x"
    print(f"  Match with original  = {aux}")

    # Prints os quantum phase

    print()
    print("=" * 60)
    print("SHOR DEMO FOR N = 15")
    print("=" * 60)

    print()
    print("--- Setting up quantum backend ---")
    sampler, backend, backend_label = get_sampler_and_backend(BACKEND_MODE, None)
    print(f"  Mode                 : {BACKEND_MODE}")
    print(f"  Backend              : {backend_label}")

    print()
    print("--- Quantum Circuit Info ---")
    print("  Target N to factor   => 15 = 3 * 5")
    print(f"  Base a for order     => 2   (chosen so gcd(a,N)=1)")
    print(f"  Control qubits       => {NUM_CONTROL_QUBITS}   (precision: 2^{NUM_CONTROL_QUBITS} = {2**NUM_CONTROL_QUBITS} states)")
    print(f"  Target qubits        => 4   (enough to represent 0..{2**4 - 1})")
    print(f"  Total qubits         => {NUM_CONTROL_QUBITS + 4}")
    print(f"  Simulation shots     => {SHOTS}")

    print()
    print("  Building quantum order-finding circuit...")
    qc = build_order_finding_circuit_N15_a2(num_control=NUM_CONTROL_QUBITS)

    print()
    print("  Submitting job...")
    counts = run_order_finding(qc, sampler, backend, shots=SHOTS)

    total_outcomes = sum(counts.values())
    print(f"  Simulation complete. Distinct outcomes: {len(counts)}, Total shots: {total_outcomes}")

    print()
    print("--- Top Measurement Results ---")
    print(f"  {'Bitstring':<12} {'Decimal':>8} {'Count':>8} {'Probability':>12}")
    print(f"  {'-'*43}|")
    for bitstring, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]:
        print(f"  {bitstring:<12} {(int(bitstring, 2)):>8} {count:>8} {(count / total_outcomes):>11.2%} |")
    print(f"  {'-'*43}|")

    # Prints of classical post processing 

    print()
    print("--- Candidate Orders (Phase Estimation) ---")
    print(f"  Phase = decimal / 2^{NUM_CONTROL_QUBITS},  then approximate as p/q via continued fractions")
    print("  The denominator q is the candidate order r")

    print()
    print(f"  {'Bitstring':<12} {'Count':>6} {'Phase':>9} {'≈ Fraction':>12} {'r (order)':>10} {'Valid?':>8}")
    print(f"  {'-'*63}|")

    candidates = extract_order_candidates(counts, num_control=NUM_CONTROL_QUBITS, N=15)

    for c in candidates[:8]:
        r = c['r']
        valid_str = ""
        if (r is not None and r % 2 == 0 and pow(2, r, 15) == 1):
            valid_str = "YES ✓"
        elif r is not None and r % 2 != 0:
            valid_str = "odd"
        else:
            valid_str = "-"   
        print(
            f"  {c['bitstring']:<12} {c['count']:>6} {c['phase']:>9.5f} {c['fraction']:>12} {str(r):>10} {valid_str:>8} |"
        )
    print(f"  {'-'*63}|")


    print()
    print("--- Factoring N=15 from Order ---")

    recovered_factors = None
    chosen_order = None

    for c in candidates:
        r = c["r"]
        factors = factors_from_order(a=2, N=15, r=r)
        if factors is not None:
            recovered_factors = factors
            chosen_order = r
            break

    if recovered_factors is None:
        raise RuntimeError(
            "No non-trivial factors were recovered from the candidates. On real hardware this can happen if noise dominates — try increasing SHOTS, lowering NUM_CONTROL_QUBITS, or re-running."
        )

    p_rec, q_rec = recovered_factors
    x_val = pow(2, chosen_order // 2, 15)

    print()
    print(f"  Chosen order         r  => {chosen_order}")
    print(f"  a^(r/2) mod N           => 2^{chosen_order//2} mod 15 = {x_val}")
    print(f"  gcd(x-1, N)             => gcd({x_val-1}, 15) = {gcd(x_val-1, 15)}")
    print(f"  gcd(x+1, N)             => gcd({x_val+1}, 15) = {gcd(x_val+1, 15)}")
    aux = "= YES ✓"
    if  p_rec * q_rec != 15:
        aux= "≠ NO ✗" 
    print(f"  Recovered factors       => {p_rec} × {q_rec} = {p_rec * q_rec} {aux}")

    print()
    print("--- RSA Private Key Recovery ---")
    cracked_rsa = build_toy_rsa(p_rec, q_rec, rsa.e)
    print(f"  Recovered p              = {p_rec}")
    print(f"  Recovered q              = {q_rec}")
    print(f"  Recovered phi(N)         = {cracked_rsa.phi}")
    print(f"  Known public exponent e  = {cracked_rsa.e}")
    
    if cracked_rsa.d == rsa.d:
        aux = "YES ✓"
    else:
        aux="NO ✗"
    print(f"  Recovered private key d  = {cracked_rsa.d}  (matches original: {aux})")

    print()
    print("--- Final Decryption with Cracked Key ---")
    recovered_word = decrypt_word(ciphertext_blocks, cracked_rsa)
    print(f"  Ciphertext blocks        = {ciphertext_blocks}")
    print(f"  Decrypted word           = '{recovered_word}'")
    match = ""
    if recovered_word.upper() == PLAINTEXT_WORD.upper():
        match="YES ✓"
    else:
        match="NO ✗"
    print(f"  Matches original         = {match}")

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Backend used             : {backend_label}")
    print(f"  Original plaintext       : '{PLAINTEXT_WORD.upper()}'")
    print(f"  Encrypted (public key)   : {ciphertext_blocks}")
    print(f"  Decrypted (private key)  : '{recovered_classically}'")
    print(f"  Shor found order r       : {chosen_order}  =>  factors {p_rec} × {q_rec}")
    print(f"  Cracked & decrypted      : '{recovered_word}'")
    print("=" * 60)


if __name__ == "__main__":
    main()
