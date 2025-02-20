import os
import shutil
import tempfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.responses import FileResponse
import yt_dlp
import whisper

app = FastAPI()

# Cargar el modelo Whisper una sola vez para reutilizarlo en cada petición
model = whisper.load_model("base")

class URLList(BaseModel):
    urls: List[str]

def descargar_audio(url: str, output_dir: str):
    """Descarga solo el audio del vídeo de Vimeo y lo guarda en el directorio indicado."""
    output_audio_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    opciones = {
        "format": "bestaudio",
        "outtmpl": output_audio_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        ydl.download([url])

def transcribir_audio(audio_path: str, output_text_path: str):
    """Transcribe el audio y guarda la transcripción en un archivo de texto."""
    result = model.transcribe(audio_path)
    with open(output_text_path, "w", encoding="utf-8") as text_file:
        text_file.write(result["text"])

@app.post("/transcribir")
async def transcribir_urls(data: URLList):
    if not data.urls:
        raise HTTPException(status_code=400, detail="No se proporcionaron URLs.")
    
    # Crear un directorio temporal para evitar problemas de permisos y concurrencia.
    with tempfile.TemporaryDirectory() as tmpdir:
        folder_audio = os.path.join(tmpdir, "audios")
        folder_transcriptions = os.path.join(tmpdir, "transcriptions")
        os.makedirs(folder_audio, exist_ok=True)
        os.makedirs(folder_transcriptions, exist_ok=True)

        for url in data.urls:
            try:
                # Descargar el audio en la carpeta "audios"
                descargar_audio(url, folder_audio)
            except Exception as e:
                print(f"Error al descargar {url}: {e}")
                continue

            # Buscar el archivo mp3 descargado
            mp3_files = [f for f in os.listdir(folder_audio) if f.endswith(".mp3")]
            if not mp3_files:
                print(f"⚠️ No se encontró el archivo descargado para {url}")
                continue

            audio_file = os.path.join(folder_audio, mp3_files[0])
            transcription_file = os.path.join(folder_transcriptions, f"{os.path.splitext(mp3_files[0])[0]}.txt")
            try:
                transcribir_audio(audio_file, transcription_file)
            except Exception as e:
                print(f"Error al transcribir {audio_file}: {e}")
                continue
            # Eliminar el audio una vez transcrito
            os.remove(audio_file)

        # Comprimir la carpeta de transcripciones en un zip
        zip_filename = os.path.join(tmpdir, "transcriptions.zip")
        shutil.make_archive(base_name=zip_filename.replace('.zip',''), format="zip", root_dir=folder_transcriptions)

        return FileResponse(zip_filename, filename="transcriptions.zip", media_type="application/zip")
