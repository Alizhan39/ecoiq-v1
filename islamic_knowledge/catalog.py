"""Offline reference indexes, not reviewed interpretation or decision evidence."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

CONTENT = Path(__file__).resolve().parents[1] / 'content' / 'islamic_knowledge'


@dataclass(frozen=True)
class Surah:
    number: int
    arabic: str
    transliteration: str
    ayah_count: int


@dataclass(frozen=True)
class DivineName:
    key: str
    ordinal: int
    arabic: str
    transliteration: str
    enumeration: str
    source_url: str
    authentication: str
    review_status: str


def _read(filename: str) -> dict:
    data = json.loads((CONTENT / filename).read_text(encoding='utf-8'))
    if data['schema_version'] != 1 or data['authoritative'] is not False:
        raise ValueError('Reference index must be version 1 and non-authoritative.')
    return data


@lru_cache(maxsize=1)
def surahs() -> Mapping[int, Surah]:
    data = _read('quran_index.json')
    if data['numbering'] != 'hafs_standard':
        raise ValueError('Unknown Quran numbering convention.')
    rows = tuple(Surah(**row) for row in data['surahs'])
    if sorted(row.number for row in rows) != list(range(1, 115)):
        raise ValueError('Surah index must cover 1–114 exactly once.')
    if any(type(row.number) is not int or type(row.ayah_count) is not int
           or row.ayah_count < 1 or not row.arabic.strip()
           or not row.transliteration.strip() for row in rows):
        raise ValueError('Invalid surah metadata.')
    return MappingProxyType({row.number: row for row in rows})


@lru_cache(maxsize=1)
def divine_names() -> Mapping[str, DivineName]:
    data = _read('names99.json')
    if data.get('review_status') != 'scholar_review_pending':
        raise ValueError('Name inventory review is still pending.')
    metadata = {key: data[key] for key in ('enumeration', 'source_url', 'authentication', 'review_status')}
    rows = tuple(DivineName(**row, **metadata) for row in data['names'])
    if sorted(row.ordinal for row in rows) != list(range(1, 100)):
        raise ValueError('Name index must cover 1–99 exactly once.')
    if len({row.key for row in rows}) != len(rows):
        raise ValueError('Name keys must be unique within this enumeration.')
    if len({row.arabic for row in rows}) != len(rows):
        raise ValueError('Duplicate Arabic name in this enumeration.')
    for row in rows:
        if (type(row.ordinal) is not int or not row.key.strip() or not row.arabic.strip()
                or not row.transliteration.strip() or row.enumeration != data['enumeration']
                or row.source_url != data['source_url']
                or row.authentication != data['authentication']
                or row.review_status != 'scholar_review_pending'):
            raise ValueError('Name inventory must retain its source, variant and pending review.')
    return MappingProxyType({row.key: row for row in rows})


@dataclass(frozen=True)
class QuranReference:
    surah: int
    ayah_start: int
    ayah_end: int | None = None

    def __post_init__(self) -> None:
        if type(self.surah) is not int or self.surah not in surahs():
            raise ValueError('Surah must be an integer between 1 and 114.')
        end = self.ayah_start if self.ayah_end is None else self.ayah_end
        if (type(self.ayah_start) is not int or type(end) is not int
                or not 1 <= self.ayah_start <= end <= surahs()[self.surah].ayah_count):
            raise ValueError('Ayah range is outside the declared Hafs surah.')

    @property
    def locator(self) -> str:
        if self.ayah_end is None or self.ayah_end == self.ayah_start:
            return f'{self.surah}:{self.ayah_start}'
        return f'{self.surah}:{self.ayah_start}-{self.ayah_end}'
