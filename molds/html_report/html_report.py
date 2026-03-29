"""
Generate a standalone HTML report from JSON/CSV data.

Arrays of objects render as sortable tables.
Single objects render as key-value cards.
Supports title, description, and theme customization.

Usage:
  fimod s -i data.json -m @html_report -o report.html
  fimod s -i data.csv  -m @html_report --arg title="Sales Q1" -o report.html
  curl -s API_URL | fimod s -m @html_report --arg title="API Response"
"""
# fimod: output-format=txt

def transform(data, args, **_):
    title = args.get("title", "Report")
    description = args.get("description", "")
    theme = args.get("theme", "light")

    # Normalize data shape
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], dict):
            kind = "table"
            # Collect all unique keys preserving order
            columns = []
            seen = {}
            for row in data:
                for k in row:
                    if k not in seen:
                        seen[k] = True
                        columns.append(k)
        else:
            kind = "list"
            columns = []
    elif isinstance(data, dict):
        kind = "object"
        columns = []
    else:
        kind = "scalar"
        columns = []

    ctx = {
        "title": title,
        "description": description,
        "theme": theme,
        "kind": kind,
        "columns": columns,
        "data": data,
        "row_count": len(data) if isinstance(data, list) else 0,
        "col_count": len(columns),
    }

    return tpl_render_from_mold("templates/report.html.j2", ctx, True)
