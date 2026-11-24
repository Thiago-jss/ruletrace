from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

path = Path(__file__).resolve().parents[1] / "corpus/credenciamento.pdf"
pdf = Canvas(str(path), invariant=1)
pdf.setTitle("Festival Horizonte - Credenciamento (fictício)")
text = pdf.beginText(55, 770)
for line in [
    "Art. 9 - Credenciamento",
    "O crachá deve ser retirado na recepção principal mediante apresentação",
    "do protocolo EVT e de documento com foto.",
    "A retirada do crachá abre às 07h15 no dia do festival.",
]:
    text.textLine(line)
pdf.drawText(text)
pdf.showPage()
pdf.save()
