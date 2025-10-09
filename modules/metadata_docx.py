import zipfile
import xml.etree.ElementTree as ET

def extract_metadata(file_path):
    metadata = {
        "file_type": "docx",
        "author": "Unknown",
        "created": "Unknown",
        "modified": "Unknown",
        "application": "Unknown"
    }

    try:
        with zipfile.ZipFile(file_path, 'r') as docx:
            if "docProps/core.xml" in docx.namelist():
                core_data = docx.read("docProps/core.xml").decode('utf-8')
                core_root = ET.fromstring(core_data)

                for elem in core_root:
                    tag = elem.tag.lower()
                    if "creator" in tag:
                        metadata["author"] = elem.text
                    elif "created" in tag:
                        metadata["created"] = elem.text
                    elif "modified" in tag:
                        metadata["modified"] = elem.text

            if "docProps/app.xml" in docx.namelist():
                app_data = docx.read("docProps/app.xml").decode('utf-8')
                app_root = ET.fromstring(app_data)

                for elem in app_root:
                    if "application" in elem.tag.lower():
                        metadata["application"] = elem.text

    except Exception as e:
        print(f"[Error] Could not extract DOCX metadata: {e}")

    return metadata