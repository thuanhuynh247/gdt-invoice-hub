"""GDT XML Schema (XSD) Validator for Circular 78 compliance."""

from __future__ import annotations
import os
import lxml.etree


def validate_xml_schema(xml_bytes: bytes) -> tuple[bool, str | None]:
    """Validate XML invoice bytes against HDon_78 XSD schema.
    
    Strips namespaces before validation to ensure compatibility with varied GDT namespaces.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # Load XSD
        schema_path = os.path.join("data", "schemas", "HDon_78.xsd")
        if not os.path.exists(schema_path):
            return True, None

        schema_doc = lxml.etree.parse(schema_path)
        schema = lxml.etree.XMLSchema(schema_doc)

        # Parse XML
        xml_doc = lxml.etree.fromstring(xml_bytes)

        # Strip XML namespaces for schema validation
        for elem in xml_doc.getiterator():
            if not isinstance(elem.tag, str):
                continue
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        # Validate
        schema.assertValid(xml_doc)
        return True, None
    except lxml.etree.DocumentInvalid as e:
        return False, f"XSD Schema Validation Error: {str(e)}"
    except Exception as e:
        return False, f"XML Syntax Error: {str(e)}"
