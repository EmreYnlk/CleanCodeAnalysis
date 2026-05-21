import io
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analyzer_engine.core import kodu_analiz_et, projeyi_analiz_et


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

MAX_SINGLE_FILE_BYTES = 1_000_000
MAX_ZIP_BYTES = 10_000_000
MAX_PROJECT_FILE_BYTES = 750_000
MAX_PROJECT_TOTAL_BYTES = 5_000_000
MAX_PROJECT_FILES = 200

IGNORED_ZIP_PARTS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "site-packages",
    "__MACOSX",
}


app = FastAPI(title="Clean Code Analyzer API")


class AnalizIstegi(BaseModel):
    kaynak_kod: str


def decode_source(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def normalize_zip_path(raw_name: str) -> str | None:
    clean_name = raw_name.replace("\\", "/")
    path = PurePosixPath(clean_name)
    parts = [part for part in path.parts if part not in ("", ".")]

    if not parts or any(part == ".." for part in parts):
        return None

    if any(part in IGNORED_ZIP_PARTS for part in parts):
        return None

    if parts[-1].startswith(".") or not parts[-1].lower().endswith(".py"):
        return None

    return "/".join(parts)


def ensure_python_filename(filename: str | None) -> str:
    if not filename or not filename.lower().endswith(".py"):
        raise HTTPException(
            status_code=400,
            detail="Yalnızca Python dosyaları (.py) desteklenmektedir.",
        )
    return Path(filename).name


@app.post("/api/v1/analyze")
def analiz_baslat(istek: AnalizIstegi):
    if not istek.kaynak_kod.strip():
        raise HTTPException(status_code=400, detail="Boş kod gönderilemez.")

    try:
        rapor = kodu_analiz_et(istek.kaynak_kod)
        return {
            "mesaj": "Analiz başarıyla tamamlandı.",
            "rapor": rapor,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Analiz sırasında hata oluştu: {exc}",
        ) from exc


@app.post("/api/v1/analyze/file")
async def analiz_dosya_baslat(file: UploadFile = File(...)):
    filename = ensure_python_filename(file.filename)
    content = await file.read()

    if len(content) > MAX_SINGLE_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Dosya çok büyük. Tek dosya analizi için 1 MB sınırı uygulanır.",
        )

    content_str = decode_source(content)
    if not content_str.strip():
        raise HTTPException(status_code=400, detail="Seçilen dosya boş olamaz.")

    try:
        rapor = kodu_analiz_et(content_str, filename)
        return {
            "mesaj": "Dosya analizi başarıyla tamamlandı.",
            "rapor": rapor,
            "filename": filename,
            "content": content_str,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Dosya analizi sırasında hata oluştu: {exc}",
        ) from exc


@app.post("/api/v1/analyze/project")
async def analiz_proje_baslat(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Proje analizi için .zip uzantılı bir arşiv yükleyin.",
        )

    archive_content = await file.read()
    if len(archive_content) > MAX_ZIP_BYTES:
        raise HTTPException(
            status_code=400,
            detail="ZIP arşivi çok büyük. Proje analizi için 10 MB sınırı uygulanır.",
        )

    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_content))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Geçerli bir ZIP arşivi yükleyin.") from exc

    dosyalar = []
    total_bytes = 0

    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue

            path = normalize_zip_path(info.filename)
            if not path:
                continue

            if info.file_size > MAX_PROJECT_FILE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"{path} dosyası çok büyük. Dosya başına 750 KB sınırı uygulanır.",
                )

            total_bytes += info.file_size
            if total_bytes > MAX_PROJECT_TOTAL_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail="Python dosyalarının toplam boyutu çok büyük. 5 MB sınırı uygulanır.",
                )

            if len(dosyalar) >= MAX_PROJECT_FILES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Proje çok fazla Python dosyası içeriyor. Üst sınır: {MAX_PROJECT_FILES}.",
                )

            source = decode_source(archive.read(info))
            if source.strip():
                dosyalar.append({"path": path, "content": source})

    if not dosyalar:
        raise HTTPException(
            status_code=400,
            detail="ZIP arşivinde analiz edilebilir Python dosyası bulunamadı.",
        )

    try:
        rapor = projeyi_analiz_et(dosyalar)
        return {
            "mesaj": "Proje analizi başarıyla tamamlandı.",
            "rapor": rapor,
            "files": dosyalar,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Proje analizi sırasında hata oluştu: {exc}",
        ) from exc


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def read_index():
    return FileResponse(STATIC_DIR / "index.html")
