import pypandoc

pypandoc.convert_text(
    open("API_DOCUMENTATION.md").read(),
    "pdf",
    format="md",
    outputfile="API_DOCUMENTATION.pdf",
    extra_args=["--standalone"],
)
print("✅ PDF generado: salida.pdf")
