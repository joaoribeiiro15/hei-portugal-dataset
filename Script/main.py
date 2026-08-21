#!/usr/bin/env python3
import csv
import pathlib
import re
import zipfile
import xml.etree.ElementTree as ET

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
HEIS_DIR = ROOT_DIR / "Source" / "HEIs"
NUTS_DIR = ROOT_DIR / "Source" / "NUTS"
DEFAULT_OUTPUT_NAME = "pt-heis-2026.csv"

LEGAL_STATUS_MAP = {
    "1": "Public",
    "0": "Private",
    "2": "Concordatarian",
    "3": "Cooperative",
    "4": "Public (Military/Police)",
}

INSTITUTION_CATEGORY_MAP = {
    "1": "University",
    "2": "Non-integrated University Institute",
    "3": "Polytechnic Institute",
    "4": "Non-integrated Polytechnic School",
    "5": "Military and Police Higher Education Institution",
}

# Domain verification status, carried straight through to the output so that
# unverified scan targets can be filtered before a measurement campaign.
DOMAIN_STATUS_COLUMN = "Domain status"

EU_ALLIANCE_MAP = {
    "1": "Member of a European Universities Initiative alliance",
    "0": "Not found in European Commission sources",
}

COLUMN_ORDER = [
    "ID",
    "Name",
    "Category",
    "Institution_Category_Standardized",
    "Member_of_European_University_alliance",
    "url",
    "NUTS2",
    "NUTS2_Label",
    "NUTS3",
    "NUTS3_Label",
    "Domain_Status",
]


def _column_letters(cell_ref):
    match = re.match(r"([A-Z]+)", cell_ref)
    return match.group(1) if match else ""


def _letters_to_index(letters):
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def _load_shared_strings(archive):
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    xml = archive.read("xl/sharedStrings.xml")
    root = ET.fromstring(xml)
    namespace = root.tag.split("}")[0].strip("{") if "}" in root.tag else None
    ns = {"s": namespace} if namespace else {}
    strings = []
    path = ".//s:si" if namespace else ".//si"
    for si in root.findall(path, ns):
        text_parts = []
        t_path = ".//s:t" if namespace else ".//t"
        for t in si.findall(t_path, ns):
            text_parts.append(t.text or "")
        strings.append("".join(text_parts))
    return strings


def _read_sheet_rows(archive, shared_strings, sheet_name="xl/worksheets/sheet1.xml"):
    xml = archive.read(sheet_name)
    root = ET.fromstring(xml)
    namespace = root.tag.split("}")[0].strip("{") if "}" in root.tag else None
    ns = {"s": namespace} if namespace else {}
    row_path = ".//s:row" if namespace else ".//row"
    cell_path = "s:c" if namespace else "c"
    rows = []
    for row in root.findall(row_path, ns):
        row_data = []
        for cell in row.findall(cell_path, ns):
            ref = cell.get("r", "")
            col_index = _letters_to_index(_column_letters(ref)) if ref else len(row_data)
            while len(row_data) <= col_index:
                row_data.append("")
            cell_type = cell.get("t")
            value = ""
            if cell_type == "inlineStr":
                is_node = cell.find("s:is", ns) if namespace else cell.find("is")
                if is_node is not None:
                    t_node = is_node.find("s:t", ns) if namespace else is_node.find("t")
                    value = t_node.text if t_node is not None and t_node.text is not None else ""
            else:
                value_node = cell.find("s:v", ns) if namespace else cell.find("v")
                if value_node is not None and value_node.text is not None:
                    if cell_type == "s":
                        value = shared_strings[int(value_node.text)]
                    else:
                        value = value_node.text
            row_data[col_index] = value
        rows.append(row_data)
    return rows


def read_xlsx(path):
    with zipfile.ZipFile(path) as archive:
        shared_strings = _load_shared_strings(archive)
        rows = _read_sheet_rows(archive, shared_strings)
    if not rows:
        return []
    header = rows[0]
    data_rows = []
    for row in rows[1:]:
        if not any(value.strip() for value in row if isinstance(value, str)):
            continue
        row_dict = {}
        for idx, column in enumerate(header):
            value = row[idx] if idx < len(row) else ""
            row_dict[column] = value
        data_rows.append(row_dict)
    return data_rows


def _list_excel_files(directory):
    return sorted(
        [path for path in directory.iterdir() if path.suffix.lower() in {".xlsx", ".xls"}]
    )


def _print_tree(directory, files):
    relative = directory.relative_to(ROOT_DIR)
    print(f"{relative}/")
    if not files:
        print("  (no Excel files found)")
        return
    for file_path in files:
        print(f"  - {file_path.name}")


def _choose_excel_file(directory, label):
    files = _list_excel_files(directory)
    print(f"\nAvailable files in {label}:")
    _print_tree(directory, files)
    if not files:
        raise FileNotFoundError(f"No Excel files found in {directory}")
    print(f"\nSelect the {label} Excel file:")
    for idx, file_path in enumerate(files, start=1):
        print(f"  {idx}. {file_path.name}")
    selection = input(f"Enter a number (default 1): ").strip()
    if not selection:
        return files[0]
    if not selection.isdigit():
        print("Invalid selection. Using the default file.")
        return files[0]
    index = int(selection)
    if not 1 <= index <= len(files):
        print("Selection out of range. Using the default file.")
        return files[0]
    return files[index - 1]


def build_nuts_label_map(nuts_rows):
    label_map = {}
    for row in nuts_rows:
        code = row.get("Code 2024", "").strip()
        level = row.get("NUTS level", "").strip()
        if not code:
            continue
        if level == "1":
            label = row.get("NUTS level 1", "").strip()
        elif level == "2":
            label = row.get("NUTS level 2", "").strip()
        elif level == "3":
            label = row.get("NUTS level 3", "").strip()
        else:
            label = ""
        label_map[code] = label
    return label_map


def normalize_hei_rows(hei_rows, nuts_label_map):
    # The HEIs source contains one row per distinct institutional domain.
    # An institution that operates several independently administered domains,
    # for example faculty-level or school-level sites, is represented by one
    # base row (PT-HEI-XXX) plus one row per organic unit domain, using the
    # suffix format PT-HEI-XXX-D01. Campus splits used for NUTS 3 attribution
    # in the companion workbook (PT-HEI-XXX-1) are collapsed to the base ID
    # here, because they share a single website and would otherwise duplicate
    # scan targets.
    normalized = []
    for row in hei_rows:
        legal_status = row.get("Legal status", "").strip()
        institution_category = row.get("Institution Category", "").strip()
        alliance = row.get("Member of European University alliance", "").strip()
        nuts2_code = row.get("Region of establishment (NUTS 2)", "").strip()
        nuts3_code = row.get("Region of establishment (NUTS 3)", "").strip()
        normalized.append(
            {
                "ID": row.get("ID", "").strip(),
                "Name": row.get("Institution Name", "").strip(),
                "Category": LEGAL_STATUS_MAP.get(legal_status, legal_status),
                "Institution_Category_Standardized": INSTITUTION_CATEGORY_MAP.get(
                    institution_category, institution_category
                ),
                "Member_of_European_University_alliance": EU_ALLIANCE_MAP.get(
                    alliance, alliance
                ),
                "url": row.get("Institutional website", "").strip(),
                "NUTS2": nuts2_code,
                "NUTS2_Label": nuts_label_map.get(nuts2_code, ""),
                "NUTS3": nuts3_code,
                "NUTS3_Label": nuts_label_map.get(nuts3_code, ""),
                "Domain_Status": row.get(DOMAIN_STATUS_COLUMN, "").strip(),
            }
        )
    return normalized


def write_csv(rows, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMN_ORDER)
        writer.writeheader()
        writer.writerows(rows)


def _sanitize_filename(name):
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip()
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    if cleaned in {"", ".", ".."}:
        return ""
    return cleaned


def _choose_output_path():
    user_input = input(
        f"Enter the output CSV filename (default: {DEFAULT_OUTPUT_NAME}): "
    ).strip()
    if not user_input:
        return ROOT_DIR / DEFAULT_OUTPUT_NAME
    sanitized = _sanitize_filename(user_input)
    if not sanitized:
        return ROOT_DIR / DEFAULT_OUTPUT_NAME
    if not sanitized.lower().endswith(".csv"):
        sanitized = f"{sanitized}.csv"
    return ROOT_DIR / sanitized


def main():
    hei_path = _choose_excel_file(HEIS_DIR, "HEIs")
    nuts_path = _choose_excel_file(NUTS_DIR, "NUTS")
    hei_rows = read_xlsx(hei_path)
    nuts_rows = read_xlsx(nuts_path)
    nuts_label_map = build_nuts_label_map(nuts_rows)
    output_rows = normalize_hei_rows(hei_rows, nuts_label_map)
    output_path = _choose_output_path()
    write_csv(output_rows, output_path)
    print(f"Wrote {len(output_rows)} institutions to {output_path}")


if __name__ == "__main__":
    main()
