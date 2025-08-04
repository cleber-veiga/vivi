from pathlib import Path
import pandas as pd

from app.services.docling import DoclingPdfProcessor
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat

class BaseDocumentRead:
    """
    Classe base abstrata para read de documentos.
    
    Esta classe define a interface comum que todos os reads de documentos
    devem implementar. Serve como base para reads específicos de diferentes
    tipos de arquivo.
    """
    async def read(self, input_pdf_path: Path) -> str:
        """
        Método abstrato para reading de documentos.
        
        Este método deve ser implementado por todas as subclasses para
        converter arquivo em texto extraído.
        
        Args:
            input_pdf_path (Path): caminho do arquivo
            
        Returns:
            str: O texto extraído do documento
            
        Raises:
            NotImplementedError: Este método deve ser implementado pelas subclasses
        """
        raise NotImplementedError("Parser não implementado.")
    
class CSVRead(BaseDocumentRead):

    async def read(self, input_pdf_path: Path, separator: str = ',') -> str:
        try:
            df = pd.read_csv(input_pdf_path, sep=separator, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(input_pdf_path, sep=separator, encoding="latin1")
        except Exception as e:
            return f"Exception: Falha ao ler CSV: {e}"
        
        # Formata cada linha como chave: valor
        formatted_lines = []
        for _, row in df.iterrows():
            line = " | ".join(f"{col}: {row[col]}" for col in df.columns)
            formatted_lines.append(line)

        text_result = "\n".join(formatted_lines)
        return text_result
    
class XLSXRead(BaseDocumentRead):
    """
    Lê arquivos Excel (.xlsx) e os converte para uma representação textual formatada.
    Ideal para posterior chunking e análise semântica.
    """

    async def read(self, input_pdf_path: Path, sheet_name: str = 0) -> str:
        try:
            df = pd.read_excel(input_pdf_path, sheet_name=sheet_name, engine="openpyxl")
        except Exception as e:
            return f"Exception: Falha ao ler Excel: {e}"

        # Formata cada linha como chave: valor
        formatted_lines = []
        for _, row in df.iterrows():
            line = " | ".join(f"{col}: {row[col]}" for col in df.columns)
            formatted_lines.append(line)

        text_result = "\n".join(formatted_lines)
        return text_result
    
class MarkdownRead(BaseDocumentRead):
    """
    Lê arquivos Markdown (.md) e retorna o conteúdo bruto como texto.
    """

    async def read(self, input_pdf_path: Path) -> str:
        try:
            with open(input_pdf_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            return f"Exception: Falha ao ler Markdown: {e}"
        
class TxtRead(BaseDocumentRead):
    """
    Lê arquivos de texto simples (.txt) com encoding seguro.
    """

    async def read(self, input_pdf_path: Path) -> str:
        try:
            with open(input_pdf_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            with open(input_pdf_path, "r", encoding="latin1") as file:
                return file.read()
        except Exception as e:
            return f"Exception: Falha ao ler TXT: {e}"

class PdfRead(BaseDocumentRead):
    """
    Leitor de PDF que utiliza a classe DoclingPdfProcessor existente
    para converter o conteúdo em Markdown estruturado.
    """

    def __init__(self):
        self.processor = DoclingPdfProcessor()

    async def read(self, input_pdf_path: Path) -> str:
        try:
            markdown = self.processor.convert_pdf_to_markdown(
                input_pdf_path=input_pdf_path
            )
            return markdown
        except Exception as e:
            return f"Exception: Erro ao converter PDF com DoclingPdfProcessor: {e}"
        
class DocxRead(BaseDocumentRead):
    """
    Leitor de DOCX utilizando Docling para conversão em Markdown.
    """

    def __init__(self):
        self.converter = DocumentConverter()

    async def read(self, input_pdf_path: Path) -> str:
        try:
            result = self.converter.convert(input_pdf_path, input_format=InputFormat.DOCX)
            markdown = result.document.export_to_markdown()
            markdown += f"\n\n<!-- Documento DOCX processado via Docling -->"
            return markdown
        except Exception as e:
            return f"Exception: Erro ao converter DOCX com Docling: {e}"