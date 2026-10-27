#!/usr/bin/env python3
"""Frequency analysis and substitution-cipher tools for KryptoLib lab 2."""

from __future__ import annotations

import argparse
from collections import Counter
import math
from pathlib import Path
import random
import sys

from kryptolib.alfabety import get_alphabet
from kryptolib.preprocessing import przygotuj_tekst


def frequencies(text: str, mode: str) -> list[tuple[str, int, float]]:
    """Return every alphabet symbol, sorted by observed count (descending)."""
    alphabet = get_alphabet(mode)
    invalid = sorted(set(text) - set(alphabet))
    if invalid:
        raise ValueError(f"Characters outside {mode}: {''.join(invalid)!r}")
    counts = Counter(text)
    total = len(text)
    return sorted(
        ((char, counts[char], counts[char] / total if total else 0.0) for char in alphabet),
        key=lambda row: (-row[1], alphabet.index(row[0])),
    )


def parse_mapping(value: str, mode: str) -> dict[str, str]:
    """Parse cipher-to-plain pairs, e.g. ``X=E,Q=T``."""
    alphabet = set(get_alphabet(mode))
    mapping: dict[str, str] = {}
    used_plain: set[str] = set()
    for pair in filter(None, (part.strip().upper() for part in value.split(","))):
        if pair.count("=") != 1:
            raise ValueError(f"Invalid mapping pair {pair!r}; expected CIPHER=PLAIN")
        cipher, plain = (item.strip() for item in pair.split("="))
        if len(cipher) != 1 or len(plain) != 1 or cipher not in alphabet or plain not in alphabet:
            raise ValueError(f"Mapping {pair!r} must use one symbol from {mode} on each side")
        if cipher in mapping and mapping[cipher] != plain:
            raise ValueError(f"Cipher symbol {cipher!r} has multiple mappings")
        if plain in used_plain and mapping.get(cipher) != plain:
            raise ValueError(f"Plain symbol {plain!r} is assigned more than once")
        mapping[cipher] = plain
        used_plain.add(plain)
    return mapping


def partially_decrypt(text: str, mapping: dict[str, str]) -> str:
    """Render guessed plaintext in lowercase and unknown cipher symbols uppercase."""
    return "".join(mapping[c].lower() if c in mapping else c for c in text)


def ngram_model(reference: str, mode: str, size: int) -> tuple[dict[str, float], float]:
    alphabet = set(get_alphabet(mode))
    cleaned = przygotuj_tekst(reference, mode)
    grams = Counter(cleaned[i:i + size] for i in range(len(cleaned) - size + 1))
    if not grams:
        raise ValueError(f"Reference text must contain at least {size} {mode} symbols")
    total = sum(grams.values())
    # Add-one smoothing permits unseen n-grams without assigning zero probability.
    possibilities = len(alphabet) ** size
    denominator = total + possibilities
    scores = {gram: math.log((count + 1) / denominator) for gram, count in grams.items()}
    floor = math.log(1 / denominator)
    return scores, floor


def _score(text: str, model: dict[str, float], floor: float, size: int) -> float:
    return sum(model.get(text[i:i + size], floor) for i in range(len(text) - size + 1))


def solve_substitution(
    ciphertext: str,
    reference: str,
    mode: str,
    size: int = 3,
    iterations: int = 2500,
    seed: int = 1,
) -> tuple[str, str, float]:
    """Try a simulated-annealing substitution search using reference n-grams.

    The result is a candidate, not proof of a correct decryption. The same
    alphabet is used to prepare the ciphertext and reference text.
    """
    alphabet = get_alphabet(mode)
    cipher = przygotuj_tekst(ciphertext, mode)
    reference = przygotuj_tekst(reference, mode)
    if len(cipher) < size:
        raise ValueError(f"Ciphertext must contain at least {size} {mode} symbols")
    model, floor = ngram_model(reference, mode, size)
    observed = Counter(cipher)
    reference_counts = Counter(reference)
    cipher_rank = sorted(alphabet, key=lambda c: (-observed[c], alphabet.index(c)))
    plain_rank = sorted(alphabet, key=lambda c: (-reference_counts[c], alphabet.index(c)))
    key = list(alphabet)
    for cipher_char, plain_char in zip(cipher_rank, plain_rank):
        key[alphabet.index(cipher_char)] = plain_char

    rng = random.Random(seed)
    # Convert to character form once; each candidate scoring pass is linear.
    best_key = key[:]
    best_plain = cipher.translate(str.maketrans(alphabet, "".join(key)))
    best_score = _score(best_plain, model, floor, size)
    current_key = key[:]
    current_score = best_score
    char_to_index = {char: i for i, char in enumerate(alphabet)}
    cipher_indices = [char_to_index[c] for c in cipher]

    for step in range(max(0, iterations)):
        left, right = rng.sample(range(len(alphabet)), 2)
        current_key[left], current_key[right] = current_key[right], current_key[left]
        plain = "".join(current_key[i] for i in cipher_indices)
        score = _score(plain, model, floor, size)
        temperature = max(0.12, 4.0 * (1.0 - step / max(1, iterations)))
        if score >= current_score or rng.random() < math.exp((score - current_score) / temperature):
            current_score = score
        else:
            current_key[left], current_key[right] = current_key[right], current_key[left]
        if current_score > best_score:
            best_score = current_score
            best_key = current_key[:]
            best_plain = "".join(best_key[i] for i in cipher_indices)

    key_string = "".join(best_key)
    # Keep the score comparable across different ciphertext lengths.
    windows = max(1, len(cipher) - size + 1)
    return key_string, best_plain, best_score / windows


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ciphertext", help="path to ciphertext file")
    parser.add_argument("--mode", choices=("ALFA26", "ALFA37"), default="ALFA26")
    parser.add_argument("--mapping", default="", help="known cipher-to-plain pairs, e.g. X=E,Q=T")
    parser.add_argument("--reference", help="known-language plaintext corpus for the optional solver")
    parser.add_argument("--language", choices=("pl", "en"), help="label shown in the solver report")
    parser.add_argument("--iterations", type=int, default=2500)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--ngram", type=int, choices=(2, 3, 4), default=3)
    args = parser.parse_args(argv)

    try:
        cipher_raw = _read_text(args.ciphertext)
        cipher = przygotuj_tekst(cipher_raw, args.mode)
        if not cipher:
            raise ValueError("Ciphertext contains no symbols in the selected alphabet")
        print(f"mode={args.mode} symbols={len(cipher)}")
        print("symbol\tcount\tpercent")
        for char, count, proportion in frequencies(cipher, args.mode):
            label = "<SPACE>" if char == " " else char
            if count:
                print(f"{label}\t{count}\t{proportion * 100:.3f}%")

        mapping = parse_mapping(args.mapping, args.mode)
        if mapping:
            print("\nPARTIAL DECRYPTION (lowercase = guessed plaintext)")
            print(partially_decrypt(cipher, mapping))

        if args.reference:
            if args.language:
                print(f"\nreference_language={args.language}")
            key, plaintext, score = solve_substitution(
                cipher, _read_text(args.reference), args.mode,
                args.ngram, args.iterations, args.seed,
            )
            print(f"candidate_score_per_ngram={score:.5f}")
            print(f"candidate_cipher_to_plain_key={','.join(f'{c}={p}' for c, p in zip(get_alphabet(args.mode), key))}")
            print("CANDIDATE PLAINTEXT (verify manually; heuristic only)")
            print(plaintext)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
