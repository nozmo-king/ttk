# ttk

## THE TERMINAL KNOT

A Lynx browser based webring for sites that can be read fluently using Lynx and other command line web browsers. No CSS, no JS.

### About

THE TERMINAL KNOT is a webring celebrating the simplicity and accessibility of text-based web browsing. Sites in the ring are designed to be fully readable and navigable using terminal-based browsers like Lynx, Links, w3m, and others.

### Guidelines

- Sites must be readable in command line browsers
- No CSS
- No JavaScript

### The Ring

- **Genesis Point:** [slime.tel](https://slime.tel) - The canonical first member site where the ring begins
- **Main Site:** [ttk.onl](https://ttk.onl) - The webring's official website and hub

### Contact

- Email: jcb@slime.tel
- XMPP: blural@xmpp.jp

## Nomos prototype code

This repository now includes a runnable prototype module for Nomos design primitives:

- `nomos_proto.py`
- `tests/test_nomos_proto.py`

Run tests with:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Nomos executable blockchain

This repository includes an executable toy blockchain implementation:

- `nomos_chain.py` (CLI blockchain executable)
- `nomos_proto.py` (support primitives: radio envelope, WoT scoring, PoW personalization, swap templates)
- `tests/test_nomos_chain.py`
- `tests/test_nomos_proto.py`

### Quick start

```bash
python nomos_chain.py init --path ./nomos_chain.json --difficulty 2 --force
python nomos_chain.py submit-tx --path ./nomos_chain.json --sender genesis --recipient alice --amount 500
python nomos_chain.py mine --path ./nomos_chain.json --miner miner1
python nomos_chain.py validate --path ./nomos_chain.json
python nomos_chain.py show --path ./nomos_chain.json
```

### Run tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
