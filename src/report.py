"""report is used to generate external reports"""
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak


def dict_to_pdf(dict_data: dict[str, Any], pdf_path: str) -> None:
    # very convoluted function (please don't touch) :(
    MAX_WIDTH = A4[0] - 2*50

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = []

    def add_footer(canvas, doc):
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont("Helvetica", 10)
        width, height = A4
        # 50pt margin from right, 20pt from bottom
        canvas.drawRightString(width - 50, 20, text)
        canvas.drawCentredString(
            width / 2, 20, "https://github.com/rufusclark/Satellite-Propagation-Toolkit")

    def recursive_fmt(d: dict[str, Any], l: int = 0) -> None:
        # generates the pdf given the dict

        # ! consider each call of this function to create a single table
        # ! each function direcetly access uses the 'DOM'

        # setup
        table_data: list[list[Any]] = []

        def write_to_DOM(table_data) -> list[Any]:
            # write table data to DOM to prevent recursion being itself (causing highly irritating and unexpected behaviour)

            if table_data:
                # creat the table
                # set table width
                table = Table(table_data, (MAX_WIDTH*0.25, MAX_WIDTH*0.75))

                # table spanning styling (if applicable)
                table_spanning = [
                    # Make row 3 span across both columns
                    [('SPAN', (0, row), (1, row)),
                     ('BACKGROUND', (0, row), (1, row), colors.lightgrey),
                     ('ALIGN', (0, row), (1, row), 'CENTER'),
                     ('FONTNAME', (0, row), (1, row), 'Helvetica-Bold')]
                    for row, val in enumerate(table_data) if val[-1] == ""
                ]

                # table styling
                table.setStyle(TableStyle(
                    [
                        # ('BACKGROUND', (0, 0), (-1, 0), colors.grey),     # header row
                        # ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT')
                    ] + [item for sublist in table_spanning for item in sublist]
                ))

                elements.append(table)
            return []

        # iterate through dict
        for i, (k, v) in enumerate(d.items()):

            # handle key
            match (l, v):
                case (0, _):
                    """key is a header"""
                    if i != 0:
                        elements.append(PageBreak())
                    elements.append(
                        Paragraph(k.title(), style=styles['Heading1']))
                case (1 | 2, dict()):
                    """key is a subheader"""
                    table_data.append(
                        [Paragraph(k.title(), style=styles["Heading2"], ), ""])
                case (0 | 1 | 2 | 3, _):
                    """key is a value label"""
                    table_data.append([Paragraph(k)])
                case _:
                    raise Warning(f"Caught unsupported dict to fmt: {d}")

            if k in ["generated image", "orbital overview"]:
                """special-case handle image from url"""
                # import from filepath as value, `v``
                img = Image(v)
                w0, h0 = img.imageWidth, img.imageHeight
                img.drawWidth = MAX_WIDTH
                img.drawHeight = h0 * (MAX_WIDTH / w0)
                elements.append(img)
                continue

            # handle value
            match v:
                case dict():
                    """value is a dict"""
                    table_data = write_to_DOM(table_data)
                    recursive_fmt(v, l+1)
                case list() as lst if all(isinstance(item, dict) for item in lst):
                    """value is a list of dicts"""
                    table_data = write_to_DOM(table_data)
                    for i in v:
                        recursive_fmt(i, l+1)
                        elements.append(Spacer(1, 12))
                case list():
                    """value is a list"""
                    table_data[-1].append(
                        Paragraph('<br/>'.join(
                            [f'• {item}' for item in v]
                        ))
                    )
                case _:
                    """other (format as a string)"""
                    table_data[-1].append(Paragraph(str(v)))

            table_data = write_to_DOM(table_data)
            # elements.append(Spacer(1, 12))

    elements.append(Paragraph("Orbital Report", styles["Title"]))
    recursive_fmt(dict_data)
    doc.build(elements, onFirstPage=add_footer,
              onLaterPages=add_footer)
    print(f"Report saved to: {pdf_path}")
