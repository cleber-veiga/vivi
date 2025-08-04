from pathlib import Path
from typing import Optional
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.settings import settings
from docling.document_converter import DocumentConverter, PdfFormatOption


class DoclingPdfProcessor:
    def __init__(
        self,
        accelerator_device: AcceleratorDevice = AcceleratorDevice.CUDA,
        num_threads: int = 8,
        do_ocr: bool = False,
        do_table_structure: bool = True,
        do_cell_matching: bool = True,
        enable_profiling: bool = True,
    ):
        accelerator_options = AcceleratorOptions(
            device=accelerator_device,
            num_threads=num_threads,
        )

        pipeline_options = PdfPipelineOptions()
        pipeline_options.accelerator_options = accelerator_options
        pipeline_options.do_ocr = do_ocr
        pipeline_options.do_table_structure = do_table_structure
        pipeline_options.table_structure_options.do_cell_matching = do_cell_matching

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        if enable_profiling:
            settings.debug.profile_pipeline_timings = True

    def convert_pdf_to_markdown(
        self,
        input_pdf_path: Path,
        output_md_path: Optional[Path] = None,
        include_metadata: bool = False,
    ) -> str:
        print(f"Processing {input_pdf_path}...")

        result = self.converter.convert(input_pdf_path)
        markdown = result.document.export_to_markdown()

        if include_metadata:
            markdown += f"\n\nConversion secs: {result.timings['pipeline_total'].times}"
            markdown += f"\n\nInput file: {input_pdf_path}"

        if output_md_path:
            output_md_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            print(f"Output saved to {output_md_path}\n")

        return markdown