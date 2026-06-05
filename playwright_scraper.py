import asyncio
import tempfile
import os
from pathlib import Path
from datetime import datetime, date
import logging
import pandas as pd
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from models import CarteiraIbovespa
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


def clean_and_process_csv(csv_path: str, data_pregao: date = None) -> pd.DataFrame:
    """
    Lê o CSV, remove cabeçalhos/rodapés indesejados e adiciona coluna data_pregao.
    """
    if data_pregao is None:
        data_pregao = date.today()

    logger.info(f"Lendo CSV: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding='latin-1')

    logger.info(f"Shape inicial: {df.shape}")
    logger.info(f"Colunas: {df.columns.tolist()}")

    # Remover linhas vazias e cabeçalhos duplicados
    df = df.dropna(how='all')
    
    # Limpar espaços em branco nos nomes das colunas
    df.columns = df.columns.str.strip()

    # Remover linhas que parecem ser cabeçalhos ou rodapés
    if 'Código' in df.columns:
        df = df[df['Código'].notna()]
        df = df[~df['Código'].str.contains('Código', case=False, na=False)]

    # Mapear possíveis nomes de colunas para um padrão
    column_mapping = {
        'Código': 'codigo',
        'Code': 'codigo',
        'Ação': 'acao',
        'Asset': 'acao',
        'Asset Name': 'acao',
        'Tipo': 'tipo',
        'Type': 'tipo',
        'Qtde. Teórica': 'quantidade',
        'Quantity': 'quantidade',
        'Part. (%)': 'participacao',
        'Participation (%)': 'participacao',
    }

    # Renomear colunas que existem
    rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
    df.rename(columns=rename_dict, inplace=True)

    # Adicionar coluna data_pregao
    df['data_pregao'] = data_pregao

    # Limpar valores numéricos
    if 'quantidade' in df.columns:
        df['quantidade'] = pd.to_numeric(df['quantidade'].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0).astype(int)
    
    if 'participacao' in df.columns:
        df['participacao'] = pd.to_numeric(df['participacao'].astype(str).str.replace(',', '.'), errors='coerce')

    # Manter apenas colunas necessárias
    colunas_necessarias = ['data_pregao', 'codigo', 'acao', 'tipo', 'quantidade', 'participacao']
    df = df[[col for col in colunas_necessarias if col in df.columns]]

    logger.info(f"Shape final: {df.shape}")
    logger.info(f"Amostra dos dados:\n{df.head()}")

    return df


def save_to_database(df: pd.DataFrame, db: Session) -> int:
    """
    Salva os dados do DataFrame no banco de dados.
    Retorna o número de registros inseridos.
    """
    logger.info(f"Salvando {len(df)} registros no banco de dados...")

    count = 0
    for _, row in df.iterrows():
        try:
            # Verificar se já existe registro para esse código na mesma data
            existing = db.query(CarteiraIbovespa).filter(
                CarteiraIbovespa.data_pregao == row['data_pregao'],
                CarteiraIbovespa.codigo == row['codigo']
            ).first()

            if existing:
                # Atualizar se já existe
                existing.acao = row.get('acao')
                existing.tipo = row.get('tipo')
                existing.quantidade = row.get('quantidade', 0)
                existing.participacao = row.get('participacao')
            else:
                # Criar novo registro
                novo_registro = CarteiraIbovespa(
                    data_pregao=row['data_pregao'],
                    codigo=row['codigo'],
                    acao=row.get('acao', ''),
                    tipo=row.get('tipo'),
                    quantidade=int(row.get('quantidade', 0)),
                    participacao=row.get('participacao'),
                )
                db.add(novo_registro)

            count += 1

        except Exception as e:
            logger.error(f"Erro ao processar linha {count}: {str(e)}")
            db.rollback()
            raise

    db.commit()
    logger.info(f"{count} registros salvos com sucesso")
    return count


async def trigger_snapshot(db: Session) -> dict:
    """
    Função principal que orquestra todo o processo:
    1. Download do CSV via Playwright
    2. Limpeza e processamento com Pandas
    3. Salvamento no banco de dados
    """
    try:
        logger.info("=== Iniciando snapshot da carteira Ibovespa ===")
        
        csv_path = await download_csv_from_b3()
        logger.info(f"CSV obtido: {csv_path}")
        
        df = clean_and_process_csv(csv_path)
        logger.info(f"CSV processado: {len(df)} registros")
        
        count = save_to_database(df, db)
        logger.info(f"Snapshot concluído com sucesso: {count} registros")
        
        # Limpar arquivo temporário
        try:
            os.remove(csv_path)
        except:
            pass

        return {
            "status": "success",
            "registros_processados": count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erro na execução do snapshot: {str(e)}")
        raise
