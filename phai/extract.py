"""Extraction de noms de produits dans des titres (règles linguistiques, sans IA).

Principe : on repère un « nom de type de produit » (lampe, organizer, holder…) et on garde
les mots qui le qualifient (sunset lamp, lampe de chevet, Autostaubsauger)."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from phai import config

HEAD_FINAL = {"en", "nl", "sv"}          # le nom est en fin de groupe (sunset lamp)
COMPOUND = {"de", "nl", "sv"}            # mots composés (Autostaubsauger)
TOKEN_RE = re.compile(r"[^\W_][\w'’-]*", re.UNICODE)
SPLIT_RE = re.compile(r"[|,.!?:;()\[\]{}/\\“”\"«»–—…#@+&*=<>]+")
URL_RE = re.compile(r"https?://\S+")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def singular(tok: str, lang: str) -> str:
    t = tok.lower()
    if len(t) <= 3:
        return t
    if lang == "en":
        if t.endswith("ies") and len(t) > 4:
            return t[:-3] + "y"
        if t.endswith(("ches", "shes", "sses", "xes")):
            return t[:-2]
        if t.endswith("s") and not t.endswith(("ss", "us", "is")):
            return t[:-1]
    elif lang in ("fr", "es", "pt", "it", "nl"):
        if t.endswith("x") and lang == "fr":
            return t[:-1]
        if t.endswith("s") and not t.endswith("ss"):
            return t[:-1]
    return t


@lru_cache(maxsize=1)
def lexicon():
    d = config.discovery()
    heads = {lang: {singular(h, lang) for h in hs} for lang, hs in d["heads"].items()}
    hype = {w.lower() for w in d["hype_words"]}
    return heads, hype, {c.lower() for c in d["connectors"]}


def dedup_key(phrase: str, lang: str) -> str:
    toks = [strip_accents(singular(t, lang)) for t in TOKEN_RE.findall(phrase.lower())]
    return f"{lang}:" + " ".join(sorted(toks))


def _is_modifier(tok: str, hype: set) -> bool:
    return tok not in hype and not tok.isdigit() and len(tok) > 1 and not re.fullmatch(r"\d+\w{0,3}", tok)


def extract(text: str, lang: str) -> list[str]:
    heads_all, hype, connectors = lexicon()
    heads = heads_all.get(lang)
    if not heads or not text:
        return []
    found: list[str] = []
    text = URL_RE.sub(" ", text)
    for segment in SPLIT_RE.split(text):
        toks = [t.lower().strip("'’-") for t in TOKEN_RE.findall(segment)]
        toks = [t for t in toks if t]
        for i, tok in enumerate(toks):
            s = singular(tok, lang)
            if s in heads:
                if lang in HEAD_FINAL:
                    mods = []
                    j = i - 1
                    while j >= 0 and len(mods) < 3 and _is_modifier(toks[j], hype):
                        mods.insert(0, toks[j])
                        j -= 1
                    if mods:
                        found.append(" ".join(mods + [tok]))
                else:  # nom en début de groupe (langues romanes, polonais, allemand non composé)
                    tail = []
                    j = i + 1
                    while j < len(toks) and len(tail) < 4:
                        t = toks[j]
                        if t in connectors or _is_modifier(t, hype):
                            tail.append(t)
                            j += 1
                        else:
                            break
                    while tail and tail[-1] in connectors:
                        tail.pop()
                    if [t for t in tail if t not in connectors]:
                        found.append(" ".join([tok] + tail))
                    elif lang == "de" and i > 0 and _is_modifier(toks[i - 1], hype):
                        found.append(f"{toks[i - 1]} {tok}")
            elif lang in COMPOUND and len(s) >= 7:
                for h in heads:
                    if len(h) >= 4 and s.endswith(h) and len(s) - len(h) >= 3 and s not in hype:
                        found.append(tok)
                        break
    # Garder les groupes les plus complets : « car vacuum » est inclus dans « car vacuum cleaner ».
    def inside(a: str, b: str) -> bool:
        return a != b and f" {a} " in f" {b} "
    found = [f for f in found if not any(inside(f, g) for g in found)]
    out, seen = [], set()
    for f in found:
        k = dedup_key(f, lang)
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out
