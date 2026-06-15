import asyncio
import tempfile
import os
import shutil
from io import StringIO
from pathlib import Path
from datetime import datetime, date
import logging
import pandas as pd
from google.cloud import storage
from playwright.async_api import async_playwright
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

B3_URL = "https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm"


async def download_csv_from_b3(timeout: int = None) -> str:
    """
    Acessa a página da B3, aguarda renderização e faz download do CSV.
    Retorna o caminho do arquivo CSV.
    """
    if timeout is None:
        timeout = settings.playwright_timeout

    temp_dir = tempfile.mkdtemp()
    csv_path = None

    try:
        async with async_playwright() as p:
            logger.info("Iniciando Playwright (headless)...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(accept_downloads=True)
            
            # Interceptar downloads
            page = await context.new_page()
            
            async def handle_download(download):
                nonlocal csv_path
                csv_path = os.path.join(temp_dir, download.suggested_filename)
                await download.save_as(csv_path)
                logger.info(f"CSV baixado: {csv_path}")

            page.on("download", handle_download)

            logger.info(f"Acessando URL: {B3_URL}")
            await page.goto(B3_URL, wait_until="networkidle", timeout=timeout)

            # Aguardar a renderização da página
            await page.wait_for_timeout(2000)

            # O conteúdo real da carteira está dentro de um iframe da B3.
            logger.info("Procurando botão de download no iframe da B3...")
            iframe_locator = page.frame_locator('iframe').first
            download_button = iframe_locator.get_by_role("link", name="Download")

            if await download_button.count() > 0:
                await download_button.first.click()
                await page.wait_for_timeout(3000)  # Aguardar download
            else:
                # Fallback para links de download que possam aparecer na página principal
                download_button = page.locator('a:has-text("Download")')
                if await download_button.count() > 0:
                    await download_button.first.click()
                    await page.wait_for_timeout(3000)
                else:
                    raise Exception("Botão de download não encontrado")

            await browser.close()

    except Exception as e:
        logger.error(f"Erro ao fazer download do CSV: {str(e)}")
        raise

    if csv_path is None or not os.path.exists(csv_path):
        raise Exception("Arquivo CSV não foi baixado corretamente")

    return csv_path


def upload_to_gcs(local_file_path: str, bucket_name: str, destination_blob_name: str):
    """
    Faz o upload de um arquivo para o Google Cloud Storage.
    O GCS sobrescreve o arquivo automaticamente se já existir.
    """
    logger.info(f"Fazendo upload para gs://{bucket_name}/{destination_blob_name}")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    logger.info("Upload concluído com sucesso")


async def trigger_snapshot() -> dict:
    """
    Função principal que orquestra todo o processo:
    1. Download do CSV via Playwright (Extração)
    2. Upload do arquivo bruto para o GCS
    """
    try:
        logger.info("=== Iniciando extração da carteira Ibovespa ===")
        
        csv_path = await download_csv_from_b3()
        filename = os.path.basename(csv_path)
        destination_blob_name = f"{settings.gcs_folder}/{filename}"

        # Upload para o GCS
        upload_to_gcs(
            local_file_path=csv_path,
            bucket_name=settings.gcs_bucket_name,
            destination_blob_name=destination_blob_name
        )
        
        # Limpar arquivo temporário
        try:
            shutil.rmtree(os.path.dirname(csv_path))
        except:
            pass

        return {
            "status": "success",
            "gcs_path": f"gs://{settings.gcs_bucket_name}/{destination_blob_name}",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erro na execução do snapshot: {str(e)}")
        raise
