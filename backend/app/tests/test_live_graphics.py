"""Testes das fases de Live Graphics (L1-L5).

Cobre as partes deterministicas e sem rede do recurso:

* CRUD de cue points sincronizados ao video (L3).
* Rodizio ponderado de campanhas/anuncios (L5, ``services._choose_campaign``).
* Relatorio de exibicao de anuncios (L5, ``crud.proof_of_play(only_ads=True)``).

Usa um SQLite em memoria. Pulado quando SQLAlchemy nao esta instalado.
"""

from __future__ import annotations

import unittest
from datetime import datetime

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app import crud, models, schemas, services
    from app.database import Base

    HAS_DEPS = True
except Exception:  # noqa: BLE001
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "SQLAlchemy nao instalado neste ambiente")
class MediaCueCrudTests(unittest.TestCase):
    """CRUD de cue points (L3)."""

    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_create_list_update_delete(self) -> None:
        media_stub = type("M", (), {"id": 1})()
        with self.Session() as db:
            cue = crud.create_media_cue(
                db,
                media_stub,
                schemas.MediaCueCreate(at_seconds=5, action="show_gfx", content="Ola"),
            )
            self.assertEqual(cue.media_id, 1)
            crud.create_media_cue(
                db, media_stub, schemas.MediaCueCreate(at_seconds=1, action="clear_gfx")
            )
            cues = crud.list_media_cues(db, 1)
            self.assertEqual(len(cues), 2)
            # Ordenacao crescente por at_seconds.
            self.assertEqual([c.at_seconds for c in cues], [1, 5])

            crud.update_media_cue(db, cue, schemas.MediaCueUpdate(enabled=False))
            self.assertFalse(crud.get_media_cue(db, cue.id).enabled)

            crud.delete_media_cue(db, cue)
            self.assertEqual(len(crud.list_media_cues(db, 1)), 1)


@unittest.skipUnless(HAS_DEPS, "SQLAlchemy nao instalado neste ambiente")
class WeightedRotationTests(unittest.TestCase):
    """Rodizio ponderado e deterministico de campanhas (L5)."""

    @staticmethod
    def _camp(cid: int, priority: int, weight: int) -> "models.Campaign":
        camp = models.Campaign()
        camp.id = cid
        camp.priority = priority
        camp.weight = weight
        return camp

    def test_single_campaign_is_returned(self) -> None:
        camp = self._camp(1, 0, 1)
        chosen = services._choose_campaign([camp], datetime(2026, 1, 1, 9, 0))
        self.assertIs(chosen, camp)

    def test_priority_dominates_weight(self) -> None:
        high = self._camp(1, 10, 1)
        low = self._camp(2, 0, 999)
        for minute in (0, 10, 20, 30, 40, 50):
            chosen = services._choose_campaign([high, low], datetime(2026, 1, 1, 9, minute))
            self.assertIs(chosen, high)

    def test_weight_changes_share(self) -> None:
        heavy = self._camp(1, 0, 3)
        light = self._camp(2, 0, 1)
        counts = {1: 0, 2: 0}
        for minute in (0, 10, 20, 30, 40, 50):
            chosen = services._choose_campaign([heavy, light], datetime(2026, 1, 1, 9, minute))
            counts[chosen.id] += 1
        # A campanha de maior peso aparece estritamente mais vezes.
        self.assertGreater(counts[1], counts[2])

    def test_zero_weight_excluded_when_others_have_weight(self) -> None:
        active = self._camp(1, 0, 2)
        zero = self._camp(2, 0, 0)
        for minute in (0, 10, 20, 30, 40, 50):
            chosen = services._choose_campaign([active, zero], datetime(2026, 1, 1, 9, minute))
            self.assertIs(chosen, active)

    def test_empty_returns_none(self) -> None:
        self.assertIsNone(services._choose_campaign([], datetime(2026, 1, 1, 9, 0)))


@unittest.skipUnless(HAS_DEPS, "SQLAlchemy nao instalado neste ambiente")
class ProofOfPlayAdsTests(unittest.TestCase):
    """Relatorio de exibicao de anuncios (L5)."""

    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _event(self, media_id, name, seconds, is_ad):
        return schemas.PlayEventCreate(
            media_id=media_id,
            zone_id=None,
            media_name=name,
            media_type="image",
            duration_seconds=seconds,
            is_ad=is_ad,
        )

    def test_only_ads_filters_out_regular_plays(self) -> None:
        with self.Session() as db:
            crud.record_play_events(
                db,
                screen_slug="loja-1",
                events=[
                    self._event(1, "Conteudo", 10, False),
                    self._event(2, "Anuncio X", 15, True),
                    self._event(2, "Anuncio X", 15, True),
                ],
            )
            todos = crud.proof_of_play(db, limit=10)
            self.assertEqual(len(todos), 2)

            ads = crud.proof_of_play(db, limit=10, only_ads=True)
            self.assertEqual(len(ads), 1)
            self.assertEqual(ads[0].media_id, 2)
            self.assertEqual(ads[0].plays, 2)
            self.assertEqual(ads[0].total_seconds, 30)


if __name__ == "__main__":
    unittest.main()
