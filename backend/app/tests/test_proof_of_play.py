"""Teste de ponta a ponta da telemetria de reprodução (proof-of-play).

Grava eventos em um SQLite em memória e valida a agregação por mídia.
Pulado quando SQLAlchemy não está instalado.
"""

from __future__ import annotations

import unittest

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app import crud, schemas
    from app.database import Base

    HAS_DEPS = True
except Exception:  # noqa: BLE001
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "SQLAlchemy não instalado neste ambiente")
class ProofOfPlayTests(unittest.TestCase):
    """Cobre gravação em lote e agregação de eventos."""

    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _event(self, media_id, name, seconds):
        return schemas.PlayEventCreate(
            media_id=media_id,
            zone_id=None,
            media_name=name,
            media_type="image",
            duration_seconds=seconds,
        )

    def test_record_and_aggregate(self) -> None:
        with self.Session() as db:
            stored = crud.record_play_events(
                db,
                screen_slug="loja-1",
                events=[
                    self._event(1, "Banner A", 10),
                    self._event(1, "Banner A", 20),
                    self._event(2, "Banner B", 5),
                ],
            )
            self.assertEqual(stored, 3)

            rows = crud.proof_of_play(db, limit=10)
            by_id = {row.media_id: row for row in rows}
            self.assertEqual(by_id[1].plays, 2)
            self.assertEqual(by_id[1].total_seconds, 30)
            self.assertEqual(by_id[2].plays, 1)
            self.assertEqual(by_id[2].total_seconds, 5)
            # Ordenação por número de reproduções (desc): Banner A primeiro.
            self.assertEqual(rows[0].media_id, 1)

    def test_screen_filter(self) -> None:
        with self.Session() as db:
            crud.record_play_events(
                db, screen_slug="loja-1", events=[self._event(1, "A", 10)]
            )
            crud.record_play_events(
                db, screen_slug="loja-2", events=[self._event(2, "B", 7)]
            )
            rows = crud.proof_of_play(db, screen_slug="loja-2", limit=10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].media_id, 2)


if __name__ == "__main__":
    unittest.main()
