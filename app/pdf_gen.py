"""Generate PDF from Services"""
import io
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def phone_format(n):
    """Format Phone String"""
    n = str(n)
    return format(int(n[:-1]), ",").replace(",", "-") + n[-1]


def generate_pdf(services):
    """Generate PDF and serve as io bytes"""
    stream = io.BytesIO()
    doc = SimpleDocTemplate(
        stream,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    logo = "/pics/icon.png"
    Story = []
    im = Image(logo, 1 * inch, 1 * inch)
    Story.append(im)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Justify", alignment=TA_JUSTIFY))
    Story.append(Spacer(1, 12))
    Story.append(Paragraph("Services", styles["Heading1"]))
    for service in services:
        Story.append(Spacer(1, 12))
        header = f"""
            {service.name}
            """

        address = (
            f"""{service.address} {service.city}, {service.state} {service.zip_code} """
        )
        web_site = f"""{service.web_site}"""
        hours = f"""
            Hours of Operation<br/>
            Days: {service.days}<br/>
            Hours: {service.hours}<br/>
            """
        Story.append(Paragraph(header, styles["Heading2"]))
        if service.address:
            Story.append(Paragraph(address, styles["Justify"]))
        if service.phone:
            phone = f"""Phone Number: {phone_format(service.phone)} """
            Story.append(Paragraph(phone, styles["Justify"]))
        if service.web_site:
            Story.append(
                Paragraph(
                    '<font color="blue"><link'
                    f' href="{web_site}">{web_site}</link></font>',
                    styles["Justify"],
                )
            )
        if service.hours:
            Story.append(Paragraph(hours, styles["Justify"]))

    Story.append(Spacer(1, 12))
    doc.build(Story)
    pdf_buffer = stream.getvalue()
    return pdf_buffer
