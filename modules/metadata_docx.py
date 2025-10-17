import zipfile
import xml.etree.ElementTree as ET

def extract_metadata(file_path):
    # Default metadata values
    metadata = {
        "file_type": "docx",
        "title": "Unknown",
        "subject": "Unknown",
        "description": "Unknown",
        "keywords": "Unknown",
        "category": "Unknown",
        "language": "Unknown",
        "author": "Unknown",
        "created": "Unknown",
        "modified": "Unknown",
        "last_modified_by": "Unknown",
        "revision": "Unknown",
        "last_printed": "Unknown",
        "created_by": "Unknown",          
        "modified_by": "Unknown",          
        "app_version": "Unknown",
        "company": "Unknown",
        "template": "Unknown",
        "total_time": "Unknown",
        "pages": "Unknown",
        "words": "Unknown",
        "characters": "Unknown",
        "characters_with_spaces": "Unknown",
        "lines": "Unknown",
        "paragraphs": "Unknown",
        "doc_security": "Unknown",
        "hyperlinks_changed": "Unknown",
        "shared_doc": "Unknown",
        "links_up_to_date": "Unknown",
        "scale_crop": "Unknown",
        "custom_properties": {},
        "has_macros": False,             
        "track_changes": False            
    }

    try:
        # Open docx 
        with zipfile.ZipFile(file_path, 'r') as z:
            names = set(z.namelist())
            
            # core.xml contains basic data
            if "docProps/core.xml" in names:
                core_root = ET.fromstring(z.read("docProps/core.xml"))
                for elem in core_root.iter():
                    tag = _local(elem.tag)
                    txt = (elem.text or "").strip() if elem.text else ""
                    if not txt:
                        continue
                    # Map XML tags to metadata fields
                    if tag == "title":
                        metadata["title"] = txt
                    elif tag == "subject":
                        metadata["subject"] = txt
                    elif tag == "description":
                        metadata["description"] = txt
                    elif tag == "keywords":
                        metadata["keywords"] = txt
                    elif tag == "category":
                        metadata["category"] = txt
                    elif tag == "language":
                        metadata["language"] = txt
                    elif tag == "creator":
                        metadata["author"] = txt
                    elif tag == "created":
                        metadata["created"] = txt
                    elif tag == "modified":
                        metadata["modified"] = txt
                    elif tag == "lastModifiedBy":
                        metadata["last_modified_by"] = txt
                    elif tag == "revision":
                        metadata["revision"] = txt
                    elif tag == "lastPrinted":
                        metadata["last_printed"] = txt

            # app.xml contains application details
            if "docProps/app.xml" in names:
                app_root = ET.fromstring(z.read("docProps/app.xml"))
                for elem in app_root.iter():
                    tag = _local(elem.tag)
                    txt = (elem.text or "").strip() if elem.text else ""
                    # Map application-level tags
                    if tag == "Application" and txt:
                        metadata["created_by"] = txt
                    elif tag == "AppVersion" and txt:
                        metadata["app_version"] = txt
                    elif tag == "Company" and txt:
                        metadata["company"] = txt
                    elif tag == "Template" and txt:
                        metadata["template"] = txt
                    elif tag == "TotalTime" and txt:
                        metadata["total_time"] = txt
                    elif tag == "Pages" and txt:
                        metadata["pages"] = txt
                    elif tag == "Words" and txt:
                        metadata["words"] = txt
                    elif tag == "Characters" and txt:
                        metadata["characters"] = txt
                    elif tag == "CharactersWithSpaces" and txt:
                        metadata["characters_with_spaces"] = txt
                    elif tag == "Lines" and txt:
                        metadata["lines"] = txt
                    elif tag == "Paragraphs" and txt:
                        metadata["paragraphs"] = txt
                    elif tag == "DocSecurity" and txt:
                        metadata["doc_security"] = txt
                    elif tag == "HyperlinksChanged" and txt:
                        metadata["hyperlinks_changed"] = txt
                    elif tag == "SharedDoc" and txt:
                        metadata["shared_doc"] = txt
                    elif tag == "LinksUpToDate" and txt:
                        metadata["links_up_to_date"] = txt
                    elif tag == "ScaleCrop" and txt:
                        metadata["scale_crop"] = txt

            # custom.xml has user-defined properties
            if "docProps/custom.xml" in names:
                try:
                    cust_root = ET.fromstring(z.read("docProps/custom.xml"))
                    for prop in cust_root.iter():
                        if _local(prop.tag) != "property":
                            continue
                        name = prop.attrib.get("name")
                        if not name:
                            continue
                        val_text = None
                        for child in prop:
                            val_text = (child.text or "").strip() if child.text else ""
                            if val_text:
                                break
                        if val_text:
                            metadata["custom_properties"][name] = val_text
                except Exception:
                    pass
            
            # Detect macros
            if "word/vbaProject.bin" in names or "word/vbaData.xml" in names:
                metadata["has_macros"] = True

            # Check if track changes is enabled
            if "word/settings.xml" in names:
                try:
                    settings_root = ET.fromstring(z.read("word/settings.xml"))
                    for elem in settings_root.iter():
                        if _local(elem.tag) == "trackRevisions":
                            metadata["track_changes"] = True
                            break
                except Exception:
                    pass

            # Fill missing creator fields
            if metadata["last_modified_by"] != "Unknown":
                metadata["modified_by"] = metadata["last_modified_by"]
            if metadata["modified_by"] == "Unknown" and metadata["created_by"] != "Unknown":
                metadata["modified_by"] = metadata["created_by"]

            # Handle Google doc files
            if metadata["created_by"] == "Unknown" and metadata["author"] == "Unknown":
                metadata["created_by"] = "Google Docs / Cloud Editor (no local metadata)"
                if metadata["modified_by"] == "Unknown":
                    metadata["modified_by"] = "Google Docs / Cloud Editor (no local metadata)"

    except Exception as e:
        print(f"[Error] Could not extract DOCX metadata: {e}")

    return metadata

# Helper to strip XML namespace from tags
def _local(tag):
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag
