

from app.services.docling import DoclingPdfProcessor


async def process_pdf_chunks(
        input_pdf_path,
        include_metadata: bool = True,
):
    #Primeiro converte o PDF com Docling para MarkDown
    docling = DoclingPdfProcessor()
    result_markdown = docling.convert_pdf_to_markdown(
        input_pdf_path=input_pdf_path,
        include_metadata=include_metadata
    )

    return result_markdown