"""Testes da resolução de playlist ativa por agendamento.

A função ``crud.resolve_active_playlist_id`` opera sobre objetos com os
atributos esperados, então usamos ``SimpleNamespace`` como dublê, evitando
uma sessão de banco. O teste é pulado se SQLAlchemy não estiver instalado
(pois ``app.crud`` importa o ORM no topo do módulo).
"""

from __future__ import annotations

import datetime as dt
import unittest
from types import SimpleNamespace

try:
    from app import crud

    HAS_DEPS = True
except Exception:  # noqa: BLE001
    HAS_DEPS = False


def _schedule(
    days: str,
    start: int,
    end: int,
    *,
    priority: int = 0,
    playlist_id: int = 1,
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
) -> SimpleNamespace:
    """Cria um agendamento dublê com os campos lidos pela resolução."""
    return SimpleNamespace(
        days_of_week=days,
        start_minute=start,
        end_minute=end,
        priority=priority,
        playlist_id=playlist_id,
        start_date=start_date,
        end_date=end_date,
    )


@unittest.skipUnless(HAS_DEPS, "SQLAlchemy/FastAPI não instalados neste ambiente")
class ScheduleResolutionTests(unittest.TestCase):
    """Cobre os principais caminhos de :func:`crud.resolve_active_playlist_id`."""

    # 2026-06-12 é uma sexta-feira => weekday() == 4.
    NOW = dt.datetime(2026, 6, 12, 10, 0)

    def test_falls_back_to_default(self) -> None:
        zone = SimpleNamespace(schedules=[], default_playlist_id=99)
        self.assertEqual(crud.resolve_active_playlist_id(zone, self.NOW), 99)

    def test_active_schedule_wins_over_default(self) -> None:
        zone = SimpleNamespace(
            schedules=[_schedule("4", 9 * 60, 12 * 60, playlist_id=7)],
            default_playlist_id=99,
        )
        self.assertEqual(crud.resolve_active_playlist_id(zone, self.NOW), 7)

    def test_outside_time_window_uses_default(self) -> None:
        zone = SimpleNamespace(
            schedules=[_schedule("4", 13 * 60, 18 * 60, playlist_id=7)],
            default_playlist_id=99,
        )
        self.assertEqual(crud.resolve_active_playlist_id(zone, self.NOW), 99)

    def test_highest_priority_wins(self) -> None:
        zone = SimpleNamespace(
            schedules=[
                _schedule("4", 8 * 60, 18 * 60, priority=1, playlist_id=5),
                _schedule("4", 9 * 60, 11 * 60, priority=9, playlist_id=8),
            ],
            default_playlist_id=99,
        )
        self.assertEqual(crud.resolve_active_playlist_id(zone, self.NOW), 8)

    def test_campaign_date_range_excludes_outside_dates(self) -> None:
        zone = SimpleNamespace(
            schedules=[
                _schedule(
                    "4",
                    9 * 60,
                    12 * 60,
                    playlist_id=7,
                    start_date=dt.date(2026, 7, 1),
                    end_date=dt.date(2026, 7, 31),
                )
            ],
            default_playlist_id=99,
        )
        # NOW (junho) está antes da campanha (julho) => usa o default.
        self.assertEqual(crud.resolve_active_playlist_id(zone, self.NOW), 99)


if __name__ == "__main__":
    unittest.main()
