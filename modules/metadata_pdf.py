import re

def extract_metadata(file_path):
    # Default PDF metadata container
    metadata = {
        "file_type": "pdf",
        "title": "Unknown",
        "author": "Unknown",
        "subject": "Unknown",
        "keywords": "Unknown",
        "creator": "Unknown",      # App that created the content
        "producer": "Unknown",     # App that produced the PDF
        "created": "Unknown",      # /CreationDate
        "modified": "Unknown",     # /ModDate
        "xmp_create": "Unknown",   # XMP CreateDate
        "xmp_modify": "Unknown",   # XMP ModifyDate
        "xmp_creator_tool": "Unknown",
        "xmp_document_id": "Unknown",
        "xmp_instance_id": "Unknown",
        "created_by": "Unknown",   # Normalised creator name
        "modified_by": "Unknown",  # Normalised producer name
        "pdf_version": "Unknown",
        "page_count": "Unknown",
        "page_width": "Unknown",
        "page_height": "Unknown",
        "encrypted": False,
        "linearized": False,
        "has_acroform": False,
        "has_annotations": False,
        "has_javascript": False,
        "trailer_id": "Unknown"    # /ID [ <hex1> <hex2> ]
    }

    try:
        with open(file_path, 'rb') as f:
            raw = f.read()  # Read full file

        text = raw.decode('latin-1', errors='ignore')  # Lenient decode

        # Extract %PDF-x.y version
        m = re.search(r'%PDF-(\d\.\d+)', text)
        if m:
            metadata["pdf_version"] = m.group(1)

        # Quick header scan: linearization flag; global scan: encryption
        head_chunk = text[:4096]
        metadata["linearized"] = ("/Linearized" in head_chunk)
        metadata["encrypted"] = ("/Encrypt" in text)

        # Helper: grab simple (/Key (Value)) pairs
        def _grab(name):
            pat = rf'/{name}\s*\((.*?)\)'
            m = re.search(pat, text, flags=re.DOTALL)
            return _clean_pdf_string(m.group(1)) if m else "Unknown"

        # Basic Info dictionary fields
        metadata["title"]    = _grab("Title")
        metadata["author"]   = _grab("Author")
        metadata["subject"]  = _grab("Subject")
        metadata["keywords"] = _grab("Keywords")
        metadata["creator"]  = _grab("Creator")
        metadata["producer"] = _grab("Producer")
        metadata["created"]  = _grab("CreationDate")
        metadata["modified"] = _grab("ModDate")

        # XMP packet (if present)
        xmp = _extract_xmp(text)
        if xmp:
            metadata["xmp_create"]       = _xml_tag(xmp, r'(?:(?:xmp|xmpMM|pdfx):)?CreateDate')
            metadata["xmp_modify"]       = _xml_tag(xmp, r'(?:(?:xmp|xmpMM|pdfx):)?ModifyDate')
            metadata["xmp_creator_tool"] = _xml_tag(xmp, r'(?:(?:xmp|xmpMM|pdfx):)?CreatorTool')
            metadata["xmp_document_id"]  = _xml_tag(xmp, r'(?:xmpMM:DocumentID)')
            metadata["xmp_instance_id"]  = _xml_tag(xmp, r'(?:xmpMM:InstanceID)')

            # Prefer XMP dates/tools if Info fields missing
            if metadata["created"] == "Unknown" and metadata["xmp_create"] != "Unknown":
                metadata["created"] = metadata["xmp_create"]
            if metadata["modified"] == "Unknown" and metadata["xmp_modify"] != "Unknown":
                metadata["modified"] = metadata["xmp_modify"]
            if metadata["creator"] == "Unknown" and metadata["xmp_creator_tool"] != "Unknown":
                metadata["creator"] = metadata["xmp_creator_tool"]

        # Trailer /ID
        m = re.search(r'/ID\s*\[\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\]', text)
        if m:
            metadata["trailer_id"] = f"{m.group(1)} {m.group(2)}"

        # Heuristics for pages and first page size
        metadata["page_count"] = text.count("/Type /Page") or "Unknown"
        metadata["page_width"], metadata["page_height"] = _first_page_mediabox(text)

        # Feature flags (forms, annots, JS)
        metadata["has_acroform"]    = ("/AcroForm" in text)
        metadata["has_annotations"] = ("/Annots" in text)
        metadata["has_javascript"]  = ("/JavaScript" in text) or ("/AA" in text)

        # Normalised creator/producer labels
        created_by  = metadata["creator"]  if metadata["creator"]  != "Unknown" else metadata["producer"]
        modified_by = metadata["producer"] if metadata["producer"] != "Unknown" else metadata["creator"]
        metadata["created_by"]  = _normalize_app(created_by)
        metadata["modified_by"] = _normalize_app(modified_by)

    except Exception as e:
        print(f"[Error] Could not extract PDF metadata: {e}")  # Log error

    return metadata  # Return filled dict

def _clean_pdf_string(s: str) -> str:
    """Unescape PDF string escapes; trim."""
    if s is None:
        return "Unknown"
    s = s.replace(r'\(', '(').replace(r'\)', ')')
    s = s.replace(r'\n', '\n').replace(r'\r', '\r').replace(r'\t', '\t')
    return s.strip() if s.strip() else "Unknown"

def _extract_xmp(text: str) -> str | None:
    # Grab full XMP packet if embedded
    m = re.search(r'(<x:xmpmeta[\s\S]+?</x:xmpmeta>)', text)
    return m.group(1) if m else None

def _xml_tag(xmp: str, qname_regex: str) -> str:
    # Extract value for a namespaced XMP tag
    m = re.search(rf'<{qname_regex}[^>]*>(.*?)</{qname_regex}>', xmp, flags=re.DOTALL)
    if m:
        return m.group(1).strip() or "Unknown"
    return "Unknown"

def _first_page_mediabox(text: str):
    """
    Find MediaBox near first /Type /Page; return (w, h) or Unknown.
    """
    pos = text.find("/Type /Page")
    if pos == -1:
        return ("Unknown", "Unknown")

    window = text[pos:pos+4000]  # Local search window
    m = re.search(r'/MediaBox\s*\[\s*([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s*\]', window)
    if not m:
        return ("Unknown", "Unknown")
    try:
        x0, y0, x1, y1 = map(float, m.groups())
        w = x1 - x0
        h = y1 - y0
        # Cast to int if integral
        w = int(w) if abs(w - int(w)) < 1e-6 else w
        h = int(h) if abs(h - int(h)) < 1e-6 else h
        return (str(w), str(h))
    except:
        return ("Unknown", "Unknown")

def _normalize_app(s: str) -> str:
    #Map nisy creator/producer strings to friendly names.
    if not s or s == "Unknown":
        return "Unknown"
    sl = s.lower()
    if "microsoft word" in sl: return "Microsoft Word"
    if "word" in sl and "microsoft" in sl: return "Microsoft Word"
    if "adobe acrobat" in sl: return "Adobe Acrobat"
    if "acrobat" in sl:       return "Adobe Acrobat"
    if "distiller" in sl:     return "Adobe Distiller"
    if "libreoffice" in sl:   return "LibreOffice"
    if "google docs" in sl:   return "Google Docs"
    if "mac os x" in sl or "quartz" in sl: return "Apple Quartz PDFContext"
    if "itext" in sl:         return "iText"
    if "wkhtmltopdf" in sl:   return "wkhtmltopdf"
    if "prince" in sl:        return "Prince"
    if "ghostscript" in sl:   return "Ghostscript"
    return s