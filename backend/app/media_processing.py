"""Processamento server-side de midia (Fase 2).

Reescala de imagens (Pillow) e transcodificacao de video (ffmpeg/ffprobe) para
adequar o tamanho/peso do arquivo a resolucao real das telas, sem perda visivel
de qualidade. O original e sempre preservado como backup; quando geramos uma
versao otimizada, ela e servida no lugar do original.

Tudo aqui e *best-effort* e degrada com seguranca:

* Imagens usam Pillow (``PIL``). Se o Pillow nao estiver instalado, a etapa e
  ignorada (status ``skipped``) e o arquivo original continua sendo servido.
* Videos usam ``ffmpeg``/``ffprobe`` do sistema (no PATH). Se nao existirem, a
  transcodificacao e ignorada; quando ao menos o ``ffprobe`` existe, ainda
  registramos as dimensoes do video.

Nenhuma funcao deste modulo levanta excecao: falhas viram status ``failed`` com
uma nota de diagnostico.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .config import settings

logger = logging.getLogger("tvmedia.media_processing")

# Formatos rasterizados que o Pillow consegue reescalar com seguranca.
# (SVG e vetorial; GIF costuma ser animado -> mantidos sem reescala.)
_PILLOW_RESIZABLE = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def pillow_available() -> bool:
    """True se a biblioteca Pillow puder ser importada."""
    try:
        import PIL  # noqa: F401

        return True
    except Exception:
        return False


def ffmpeg_bin() -> str | None:
    """Caminho do binario ffmpeg, ou None se ausente."""
    return shutil.which("ffmpeg")


def ffprobe_bin() -> str | None:
    """Caminho do binario ffprobe, ou None se ausente."""
    return shutil.which("ffprobe")


def capabilities() -> dict:
    """Resumo do que esta disponivel no ambiente atual."""
    return {
        "pillow": pillow_available(),
        "ffmpeg": ffmpeg_bin() is not None,
        "ffprobe": ffprobe_bin() is not None,
    }


def _empty_result(status: str = "done", note: str | None = None) -> dict:
    return {
        "status": status,
        "note": note,
        "width": None,
        "height": None,
        "optimized_path": None,
        "poster_path": None,
    }


def _probe_video_dimensions(abs_path: Path) -> tuple[int | None, int | None]:
    """Le largura/altura do primeiro fluxo de video via ffprobe."""
    probe = ffprobe_bin()
    if not probe:
        return None, None
    try:
        out = subprocess.run(
            [
                probe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0:s=x",
                str(abs_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        token = ""
        if out.stdout and out.stdout.strip():
            token = out.stdout.strip().splitlines()[0].strip()
        if "x" in token:
            w_s, _, h_s = token.partition("x")
            return int(float(w_s)), int(float(h_s))
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("ffprobe falhou para %s: %s", abs_path, exc)
    return None, None


def _process_image(media_dir: Path, rel_path: str) -> dict:
    """Captura dimensoes e, se necessario, gera versao reescalada da imagem."""
    result = _empty_result()
    if not pillow_available():
        result["status"] = "skipped"
        result["note"] = "Pillow nao instalado; imagem servida no original."
        return result

    from PIL import Image, ImageOps

    abs_path = media_dir / rel_path
    suffix = abs_path.suffix.lower()
    try:
        with Image.open(abs_path) as img:
            img = ImageOps.exif_transpose(img)
            orig_w, orig_h = img.size
            # Sempre registramos as dimensoes ORIGINAIS (refletem a qualidade
            # da fonte; usadas no aviso de baixa resolucao do painel).
            result["width"] = orig_w
            result["height"] = orig_h

            if suffix not in _PILLOW_RESIZABLE:
                result["note"] = "Formato vetorial/animado mantido sem reescala."
                return result

            max_dim = max(1, settings.image_max_dimension)
            largest = max(orig_w, orig_h)
            if largest <= max_dim:
                result["note"] = "Resolucao dentro do limite; original mantido."
                return result

            scale = max_dim / float(largest)
            new_size = (
                max(1, round(orig_w * scale)),
                max(1, round(orig_h * scale)),
            )
            resized = img.resize(new_size, Image.LANCZOS)

            stem = abs_path.stem
            opt_name = f"{stem}_opt{suffix}"
            opt_abs = media_dir / opt_name
            save_kwargs: dict = {}
            if suffix in (".jpg", ".jpeg"):
                resized = resized.convert("RGB")
                save_kwargs = {
                    "quality": settings.image_quality,
                    "optimize": True,
                    "progressive": True,
                }
            elif suffix == ".webp":
                save_kwargs = {"quality": settings.image_quality, "method": 6}
            elif suffix == ".png":
                save_kwargs = {"optimize": True}
            resized.save(opt_abs, **save_kwargs)

            result["optimized_path"] = opt_name
            result["note"] = (
                f"Reescalada de {orig_w}x{orig_h} para "
                f"{new_size[0]}x{new_size[1]}."
            )
            return result
    except Exception as exc:
        result["status"] = "failed"
        result["note"] = f"Falha ao processar imagem: {exc}"[:480]
        return result


def _process_video(media_dir: Path, rel_path: str) -> dict:
    """Captura dimensoes e, se possivel, transcodifica para H.264 + poster."""
    result = _empty_result()
    abs_path = media_dir / rel_path

    w, h = _probe_video_dimensions(abs_path)
    result["width"], result["height"] = w, h

    ff = ffmpeg_bin()
    if not ff:
        result["status"] = "skipped"
        result["note"] = "ffmpeg nao encontrado; video servido no original."
        return result

    stem = abs_path.stem
    opt_name = f"{stem}_opt.mp4"
    opt_abs = media_dir / opt_name
    poster_name = f"{stem}_poster.jpg"
    poster_abs = media_dir / poster_name
    max_h = max(120, settings.video_max_height)

    try:
        # Transcodifica para H.264/AAC, faststart. O filtro reduz a altura ate
        # 'max_h' sem fazer upscaling e mantem a largura par (scale=-2).
        vf = f"scale=-2:'min(ih,{max_h})'"
        cmd = [
            ff,
            "-y",
            "-i",
            str(abs_path),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            settings.video_preset,
            "-crf",
            str(settings.video_crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(opt_abs),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.media_process_timeout,
        )
        if proc.returncode == 0 and opt_abs.exists() and opt_abs.stat().st_size > 0:
            result["optimized_path"] = opt_name
            result["note"] = f"Transcodificado para H.264 (<= {max_h}p)."
        else:
            opt_abs.unlink(missing_ok=True)
            result["status"] = "failed"
            tail = (proc.stderr or "").strip().splitlines()[-1:] or [""]
            result["note"] = f"ffmpeg retornou {proc.returncode}: {tail[0]}"[:480]

        # Poster: primeiro quadro do video original (independe da transcodificacao).
        pcmd = [
            ff,
            "-y",
            "-i",
            str(abs_path),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(poster_abs),
        ]
        pproc = subprocess.run(pcmd, capture_output=True, text=True, timeout=120)
        if (
            pproc.returncode == 0
            and poster_abs.exists()
            and poster_abs.stat().st_size > 0
        ):
            result["poster_path"] = poster_name
        else:
            poster_abs.unlink(missing_ok=True)
        return result
    except subprocess.TimeoutExpired:
        opt_abs.unlink(missing_ok=True)
        result["status"] = "failed"
        result["note"] = "Transcodificacao excedeu o tempo limite."
        return result
    except Exception as exc:
        opt_abs.unlink(missing_ok=True)
        result["status"] = "failed"
        result["note"] = f"Falha ao processar video: {exc}"[:480]
        return result


def process_media_file(media_dir, rel_path: str, media_type) -> dict:
    """Processa uma midia conforme o tipo. Nunca levanta excecao.

    Retorna um dict com as chaves: status, note, width, height,
    optimized_path, poster_path.
    """
    try:
        from . import models

        media_dir = Path(media_dir)
        if media_type == models.MediaType.image:
            return _process_image(media_dir, rel_path)
        if media_type == models.MediaType.video:
            return _process_video(media_dir, rel_path)
        return _empty_result(status="skipped", note="Tipo nao processavel.")
    except Exception as exc:  # pragma: no cover - defensivo
        return _empty_result(status="failed", note=str(exc)[:480])
