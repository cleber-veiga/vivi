import re
from typing import Optional, Tuple

VIDEO_PATTERN = re.compile(
    r"\[\[\s*VIDEO\s*:\s*key\s*=\s*([A-Za-z0-9_.\-]+)\s*\]\]",
    flags=re.IGNORECASE
)

def split_text_by_video(text: str) -> Optional[Tuple[str, str, str]]:
    """
    Procura o primeiro marcador [[VIDEO:key=...]] e divide o texto em:
    - antes (str)
    - video_key (str)
    - depois (str)
    
    Retorna None se não houver marcador de vídeo.
    """
    if not text:
        return None

    match = VIDEO_PATTERN.search(text)
    if not match:
        return None

    start, end = match.span()
    before = text[:start].rstrip()
    after = text[end:].lstrip()
    video_key = match.group(1)

    return before, video_key, after
