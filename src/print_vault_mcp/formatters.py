"""Response formatters that turn raw API JSON into concise, AI-friendly text."""

from __future__ import annotations


# -- Helpers ----------------------------------------------------------------

def _val(obj: dict, *keys, default="—"):
    """Safely extract a nested value."""
    cur = obj
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
    return cur if cur is not None else default


def _nested_name(obj: dict | None, fallback="—") -> str:
    if obj is None:
        return fallback
    if isinstance(obj, dict):
        return obj.get("name", fallback)
    return str(obj)


# -- Inventory --------------------------------------------------------------

def format_inventory_list(items: list[dict]) -> str:
    if not items:
        return "No inventory items found."
    lines = [f"Found {len(items)} inventory item(s):\n"]
    for it in items:
        brand = _nested_name(it.get("brand"))
        loc = _nested_name(it.get("location"))
        lines.append(
            f"  [{it['id']}] {it['title']}  —  qty: {it['quantity']}, "
            f"brand: {brand}, location: {loc}"
        )
    return "\n".join(lines)


def format_inventory_detail(it: dict) -> str:
    brand = _nested_name(it.get("brand"))
    pt = _nested_name(it.get("part_type"))
    loc = _nested_name(it.get("location"))
    vendor = _nested_name(it.get("vendor"))
    lines = [
        f"Inventory Item #{it['id']}: {it['title']}",
        f"  Quantity: {it['quantity']}  |  Cost: {_val(it, 'cost')}",
        f"  Brand: {brand}  |  Part Type: {pt}",
        f"  Location: {loc}  |  Vendor: {vendor}",
        f"  Consumable: {it.get('is_consumable', False)}  |  Low stock threshold: {_val(it, 'low_stock_threshold')}",
    ]
    if it.get("notes"):
        lines.append(f"  Notes: {it['notes']}")
    projects = it.get("associated_projects", [])
    if projects:
        names = ", ".join(p.get("project_name", str(p.get("id"))) for p in projects)
        lines.append(f"  Projects: {names}")
    return "\n".join(lines)


def format_allocation(data: dict) -> str:
    lines = [
        f"Allocation Summary",
        f"  On hand: {data['qty_on_hand']}  |  Needed: {data['qty_needed']}  |  Available: {data['qty_available']}",
        f"  Overallocated: {data['is_overallocated']}",
    ]
    for proj in data.get("active_projects", []):
        lines.append(f"  Active → {proj['project_name']}: {proj['qty_allocated']} allocated")
    for proj in data.get("closed_projects", []):
        lines.append(f"  Closed → {proj['project_name']}: {proj['qty_allocated']} allocated")
    return "\n".join(lines)


# -- Filament / Materials ---------------------------------------------------

def format_material_list(items: list[dict]) -> str:
    if not items:
        return "No materials found."
    lines = [f"Found {len(items)} material(s):\n"]
    for m in items:
        brand = _nested_name(m.get("brand"))
        mtype = "Generic" if m.get("is_generic") else "Blueprint"
        lines.append(
            f"  [{m['id']}] {m['name']}  ({mtype})  —  brand: {brand}, "
            f"spools: {_val(m, 'total_spool_count')}, "
            f"available: {_val(m, 'total_available_grams')}g"
        )
    return "\n".join(lines)


def format_spool_list(spools: list[dict]) -> str:
    if not spools:
        return "No spools found."
    lines = [f"Found {len(spools)} spool(s):\n"]
    for s in spools:
        ft = s.get("filament_type") or {}
        name = s.get("display_name") or ft.get("name") or s.get("standalone_name") or "Unknown"
        loc = _nested_name(s.get("location"))
        printer = _nested_name(s.get("assigned_printer"), fallback="none")
        lines.append(
            f"  [{s['id']}] {name}  —  status: {s['status']}, "
            f"weight: {s.get('current_weight', '?')}g/{s.get('initial_weight', '?')}g, "
            f"qty: {s.get('quantity', 1)}, location: {loc}, printer: {printer}"
        )
    return "\n".join(lines)


def format_spool_detail(s: dict) -> str:
    ft = s.get("filament_type") or {}
    name = s.get("display_name") or ft.get("name") or s.get("standalone_name") or "Unknown"
    lines = [
        f"Spool #{s['id']}: {name}",
        f"  Status: {s['status']}  |  Qty: {s.get('quantity', 1)}  |  Opened: {s.get('is_opened', False)}",
        f"  Weight: {s.get('current_weight', '?')}g / {s.get('initial_weight', '?')}g  "
        f"({s.get('weight_remaining_percent', '?')}% remaining)",
        f"  Location: {_nested_name(s.get('location'))}",
        f"  Printer: {_nested_name(s.get('assigned_printer'), 'none')}",
    ]
    if s.get("notes"):
        lines.append(f"  Notes: {s['notes']}")
    return "\n".join(lines)


# -- Printers ---------------------------------------------------------------

def format_printer_list(printers: list[dict]) -> str:
    if not printers:
        return "No printers found."
    lines = [f"Found {len(printers)} printer(s):\n"]
    for p in printers:
        mfg = _nested_name(p.get("manufacturer"))
        lines.append(
            f"  [{p['id']}] {p['title']}  —  mfg: {mfg}, status: {p.get('status', '—')}"
        )
    return "\n".join(lines)


def format_printer_detail(p: dict) -> str:
    mfg = _nested_name(p.get("manufacturer"))
    lines = [
        f"Printer #{p['id']}: {p['title']}",
        f"  Manufacturer: {mfg}  |  Status: {p.get('status', '—')}",
        f"  Serial: {_val(p, 'serial_number')}  |  Purchased: {_val(p, 'purchase_date')}",
    ]
    mods = p.get("mods", [])
    if mods:
        lines.append(f"  Mods ({len(mods)}):")
        for mod in mods:
            lines.append(f"    - {mod['name']} [{mod.get('status', '?')}]")
    if p.get("notes"):
        lines.append(f"  Notes: {p['notes']}")
    return "\n".join(lines)


# -- Projects ---------------------------------------------------------------

def format_project_list(projects: list[dict]) -> str:
    if not projects:
        return "No projects found."
    lines = [f"Found {len(projects)} project(s):\n"]
    for p in projects:
        lines.append(
            f"  [{p['id']}] {p['project_name']}  —  status: {p['status']}, "
            f"due: {_val(p, 'due_date')}"
        )
    return "\n".join(lines)


def format_project_detail(p: dict) -> str:
    lines = [
        f"Project #{p['id']}: {p['project_name']}",
        f"  Status: {p['status']}  |  Start: {_val(p, 'start_date')}  |  Due: {_val(p, 'due_date')}",
    ]
    if p.get("description"):
        lines.append(f"  Description: {p['description']}")

    bom = p.get("bom_items", [])
    if bom:
        lines.append(f"  BOM Items ({len(bom)}):")
        for b in bom:
            lines.append(
                f"    - {b.get('description', '?')} × {b.get('quantity_needed', '?')} "
                f"[{b.get('status', '?')}]"
            )

    printers = p.get("associated_printers", [])
    if printers:
        names = ", ".join(pr.get("title", str(pr.get("id"))) for pr in printers)
        lines.append(f"  Printers: {names}")

    if p.get("notes"):
        lines.append(f"  Notes: {p['notes']}")
    return "\n".join(lines)


def format_shopping_list(rows: list[dict]) -> str:
    if not rows:
        return "Shopping list is empty — nothing to buy!"
    lines = [f"Shopping List ({len(rows)} item(s)):\n"]
    for r in rows:
        reason = r.get("reason", "?")
        ordered = " [ORDERED]" if r.get("is_ordered") else ""
        lines.append(
            f"  • {r['description']} × {r['quantity_needed']}  "
            f"(project: {r['project_name']}, reason: {reason}){ordered}"
        )
    return "\n".join(lines)


# -- Trackers ---------------------------------------------------------------

def format_tracker_list(trackers: list[dict]) -> str:
    if not trackers:
        return "No trackers found."
    lines = [f"Found {len(trackers)} tracker(s):\n"]
    for t in trackers:
        lines.append(
            f"  [{t['id']}] {t.get('name', '—')}  —  "
            f"files: {t.get('total_files', '?')}, "
            f"printed: {t.get('printed_files', '?')}"
        )
    return "\n".join(lines)


def format_tracker_detail(t: dict) -> str:
    lines = [
        f"Tracker #{t['id']}: {t.get('name', '—')}",
        f"  GitHub: {_val(t, 'github_url')}",
        f"  Created: {_val(t, 'created_date')}  |  Updated: {_val(t, 'updated_date')}",
    ]
    files = t.get("files", [])
    if files:
        total = len(files)
        printed = sum(1 for f in files if f.get("status") == "printed")
        lines.append(f"  Progress: {printed}/{total} files printed")
        for f in files[:20]:  # Cap at 20 to avoid massive output
            lines.append(
                f"    [{f.get('id')}] {f.get('filename', '?')} "
                f"— {f.get('printed_quantity', 0)}/{f.get('quantity', 1)} "
                f"[{f.get('status', '?')}]"
            )
        if total > 20:
            lines.append(f"    ... and {total - 20} more files")
    return "\n".join(lines)


# -- Dashboard --------------------------------------------------------------

def format_dashboard(data: dict) -> str:
    stats = data.get("stats", {})
    lines = [
        "Dashboard Overview",
        f"  Inventory items: {stats.get('inventory_count', '?')}",
        f"  Printers: {stats.get('printer_count', '?')}",
        f"  Active projects: {stats.get('project_count', '?')}",
        f"  Trackers: {stats.get('tracker_count', '?')}",
    ]

    alerts = data.get("alerts", {})
    for severity in ("critical", "warning", "info"):
        alert_list = alerts.get(severity, [])
        if alert_list:
            lines.append(f"\n  {severity.upper()} alerts ({len(alert_list)}):")
            for a in alert_list:
                lines.append(f"    • {a.get('message', a.get('type', '?'))}")

    featured = data.get("featured_trackers", [])
    if featured:
        lines.append(f"\n  Featured trackers:")
        for ft in featured:
            lines.append(f"    • {ft.get('name', '?')}")

    active = data.get("active_projects", [])
    if active:
        lines.append(f"\n  Active projects:")
        for ap in active:
            lines.append(f"    • {ap.get('project_name', '?')} [{ap.get('status', '?')}]")

    return "\n".join(lines)
