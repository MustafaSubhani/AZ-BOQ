"""Element of a bill line, from the words in its description.

The first rule that fits wins. A stem matches an Azerbaijani ending: divar matches
divarların. A word matches only the whole word: nov does not match növbəti.
"""
import re

from ..rules import load
from ..text.normalise import fold_key


def classify(description: str) -> str | None:
    rule = classify_rule(description)
    return rule["element"] if rule else None


def classify_rule(description: str) -> dict | None:
    key = fold_key(description or "")
    for rule in load("bill_elements"):
        if _fits(key, rule):
            return rule
    return None


def _fits(key: str, rule: dict) -> bool:
    if rule.get("all") and not all(_stem(key, word) for word in rule["all"]):
        return False
    if rule.get("words") and not all(_word(key, word) for word in rule["words"]):
        return False
    choices = list(rule.get("any") or [])
    phrases = [fold_key(p) for p in rule.get("phrases") or []]
    if rule.get("any") or rule.get("phrases"):
        if not any(_stem(key, word) for word in choices) and not any(p in key for p in phrases):
            return False
    return bool(rule.get("all") or rule.get("words") or rule.get("any") or rule.get("phrases"))


def _stem(key: str, word: str) -> bool:
    return re.search(rf"(^|[^a-z0-9]){re.escape(fold_key(word))}", key) is not None


def _word(key: str, word: str) -> bool:
    return re.search(rf"(^|[^a-z0-9]){re.escape(fold_key(word))}([^a-z0-9]|$)", key) is not None
