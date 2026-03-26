"""Print Vault MCP Server — tool definitions and server setup."""

from __future__ import annotations

import logging
import os

import httpx
from mcp.server.fastmcp import FastMCP

from .client import PrintVaultClient
from . import formatters as fmt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server & client bootstrap
# ---------------------------------------------------------------------------

mcp = FastMCP("Print Vault")

_client: PrintVaultClient | None = None


def _get_client() -> PrintVaultClient:
    global _client
    if _client is None:
        base_url = os.environ.get("PRINT_VAULT_URL", "")
        if not base_url:
            raise RuntimeError(
                "PRINT_VAULT_URL environment variable is required. "
                "Set it to your Print Vault instance URL (e.g. http://192.168.1.100:8000)."
            )
        timeout = int(os.environ.get("PRINT_VAULT_TIMEOUT", "30"))
        _client = PrintVaultClient(base_url, timeout)
    return _client


def _err(e: Exception) -> str:
    """Format an error for the AI."""
    if isinstance(e, httpx.HTTPStatusError):
        try:
            body = e.response.json()
        except Exception:
            body = e.response.text
        return f"API error {e.response.status_code}: {body}"
    return f"Error: {e}"


# ===================================================================
# Tool Group 1: Dashboard & System
# ===================================================================

@mcp.tool()
async def get_dashboard() -> str:
    """Get a full status overview of your Print Vault: alerts, stats, featured trackers, and active projects."""
    try:
        data = await _get_client().get("/api/dashboard/")
        return fmt.format_dashboard(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_version() -> str:
    """Get the current Print Vault version."""
    try:
        data = await _get_client().get("/api/version/")
        return f"Print Vault version: {data.get('version', '?')}"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def dismiss_alert(alert_type: str, alert_id: str) -> str:
    """Dismiss a specific dashboard alert.

    Args:
        alert_type: The type of alert (e.g. 'printer_repair', 'low_stock', 'maintenance_overdue').
        alert_id: The ID of the specific alert to dismiss.
    """
    try:
        data = await _get_client().post(
            "/api/alerts/dismiss/",
            json={"alert_type": alert_type, "alert_id": alert_id},
        )
        return f"Alert dismissed: {data}"
    except Exception as e:
        return _err(e)


# ===================================================================
# Tool Group 2: Inventory Management
# ===================================================================

@mcp.tool()
async def search_inventory(
    query: str = "",
    brand: str | None = None,
    part_type: str | None = None,
    location: str | None = None,
) -> str:
    """Search inventory items by keyword, brand, part type, or location.

    Args:
        query: Free-text search across title, brand, part type, location, and notes.
        brand: Filter by brand name (exact match on brand__name).
        part_type: Filter by part type name (exact match on part_type__name).
        location: Filter by location name (exact match on location__name).
    """
    try:
        params: dict = {}
        if query:
            params["search"] = query
        if brand:
            params["brand__name"] = brand
        if part_type:
            params["part_type__name"] = part_type
        if location:
            params["location__name"] = location
        data = await _get_client().get("/api/inventoryitems/", params=params)
        return fmt.format_inventory_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_inventory_item(item_id: int) -> str:
    """Get full details on a specific inventory item.

    Args:
        item_id: The ID of the inventory item.
    """
    try:
        data = await _get_client().get(f"/api/inventoryitems/{item_id}/")
        return fmt.format_inventory_detail(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def add_inventory_item(
    title: str,
    quantity: int = 0,
    brand: str | None = None,
    part_type: str | None = None,
    location: str | None = None,
    cost: float | None = None,
    is_consumable: bool = False,
    low_stock_threshold: int | None = None,
    notes: str | None = None,
    vendor: str | None = None,
    vendor_link: str | None = None,
    model: str | None = None,
) -> str:
    """Add a new inventory item. Brand, part type, location, and vendor are created automatically if they don't exist.

    Args:
        title: Name/title of the inventory item.
        quantity: Quantity on hand.
        brand: Brand name (will be created if new).
        part_type: Part type name (will be created if new).
        location: Storage location name (will be created if new).
        cost: Unit cost.
        is_consumable: Whether this is a consumable item (enables low stock tracking).
        low_stock_threshold: Quantity threshold for low stock alerts (consumables only).
        notes: Free-text notes.
        vendor: Vendor name (will be created if new).
        vendor_link: URL to vendor product page.
        model: Model/part number.
    """
    try:
        payload: dict = {"title": title, "quantity": quantity, "is_consumable": is_consumable}
        if brand:
            payload["brand"] = {"name": brand}
        if part_type:
            payload["part_type"] = {"name": part_type}
        if location:
            payload["location"] = {"name": location}
        if vendor:
            payload["vendor"] = {"name": vendor}
        if cost is not None:
            payload["cost"] = cost
        if low_stock_threshold is not None:
            payload["low_stock_threshold"] = low_stock_threshold
        if notes:
            payload["notes"] = notes
        if vendor_link:
            payload["vendor_link"] = vendor_link
        if model:
            payload["model"] = model

        data = await _get_client().post("/api/inventoryitems/", json=payload)
        return f"Created inventory item #{data['id']}: {data['title']} (qty: {data['quantity']})"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def update_inventory_item(
    item_id: int,
    title: str | None = None,
    quantity: int | None = None,
    brand: str | None = None,
    part_type: str | None = None,
    location: str | None = None,
    cost: float | None = None,
    is_consumable: bool | None = None,
    low_stock_threshold: int | None = None,
    notes: str | None = None,
    vendor: str | None = None,
    vendor_link: str | None = None,
    model: str | None = None,
) -> str:
    """Update an existing inventory item. Only the fields you provide will be changed.

    Args:
        item_id: The ID of the inventory item to update.
        title: New title.
        quantity: New quantity on hand.
        brand: Brand name (will be created if new).
        part_type: Part type name (will be created if new).
        location: Location name (will be created if new).
        cost: Unit cost.
        is_consumable: Whether this is a consumable item.
        low_stock_threshold: Low stock alert threshold.
        notes: Free-text notes.
        vendor: Vendor name (will be created if new).
        vendor_link: URL to vendor product page.
        model: Model/part number.
    """
    try:
        payload: dict = {}
        if title is not None:
            payload["title"] = title
        if quantity is not None:
            payload["quantity"] = quantity
        if brand is not None:
            payload["brand"] = {"name": brand}
        if part_type is not None:
            payload["part_type"] = {"name": part_type}
        if location is not None:
            payload["location"] = {"name": location}
        if cost is not None:
            payload["cost"] = cost
        if is_consumable is not None:
            payload["is_consumable"] = is_consumable
        if low_stock_threshold is not None:
            payload["low_stock_threshold"] = low_stock_threshold
        if notes is not None:
            payload["notes"] = notes
        if vendor is not None:
            payload["vendor"] = {"name": vendor}
        if vendor_link is not None:
            payload["vendor_link"] = vendor_link
        if model is not None:
            payload["model"] = model

        data = await _get_client().patch(f"/api/inventoryitems/{item_id}/", json=payload)
        return f"Updated inventory item #{data['id']}: {data['title']}"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_low_stock() -> str:
    """List all consumable inventory items that are at or below their low stock threshold."""
    try:
        data = await _get_client().get("/api/low-stock/")
        return fmt.format_inventory_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_item_allocation(item_id: int) -> str:
    """Get the allocation summary for an inventory item — how much is on hand, needed, and which projects are using it.

    Args:
        item_id: The ID of the inventory item.
    """
    try:
        data = await _get_client().get(f"/api/inventoryitems/{item_id}/allocation/")
        return fmt.format_allocation(data)
    except Exception as e:
        return _err(e)


# ===================================================================
# Tool Group 3: Filament / Material Management
# ===================================================================

@mcp.tool()
async def list_materials(
    search: str = "",
    material_type: str | None = None,
    favorites: bool = False,
) -> str:
    """List filament material blueprints and generic material types.

    Args:
        search: Search by material or brand name.
        material_type: Filter by 'generic' or 'blueprint'.
        favorites: If true, show only favorited materials.
    """
    try:
        params: dict = {}
        if search:
            params["search"] = search
        if material_type:
            params["type"] = material_type
        if favorites:
            params["favorites"] = "true"
        data = await _get_client().get("/api/materials/", params=params)
        return fmt.format_material_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_material_spools(material_id: int) -> str:
    """List all physical spools for a given material blueprint.

    Args:
        material_id: The ID of the material blueprint.
    """
    try:
        data = await _get_client().get(f"/api/materials/{material_id}/spools/")
        return fmt.format_spool_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def create_material(
    name: str,
    is_generic: bool = False,
    brand: str | None = None,
    base_material_id: int | None = None,
    colors: list[str] | None = None,
    color_family: str | None = None,
    diameter: float | None = None,
    spool_weight: int | None = None,
    empty_spool_weight: int | None = None,
    nozzle_temp_min: int | None = None,
    nozzle_temp_max: int | None = None,
    bed_temp_min: int | None = None,
    bed_temp_max: int | None = None,
    density: float | None = None,
    price_per_spool: float | None = None,
    vendor: str | None = None,
    vendor_link: str | None = None,
    notes: str | None = None,
    features: list[str] | None = None,
) -> str:
    """Create a new material — either a generic type (e.g. 'PLA') or a specific blueprint (e.g. 'Sunlu PLA+ Black').

    A generic material is a base type that blueprints reference. A blueprint is a specific
    brand/color combination that spools are linked to. Create a generic first, then blueprints
    that reference it via base_material_id.

    Args:
        name: Material name (e.g. 'PLA' for generic, 'Sunlu PLA+ Black' for blueprint).
        is_generic: True for a generic base material, False for a specific blueprint.
        brand: Brand name for blueprints (will be created if new). Ignored for generics.
        base_material_id: ID of a generic material this blueprint is based on.
        colors: List of color names (e.g. ['Black'] or ['Black', 'Red'] for multicolor).
        color_family: Color family for grouping (e.g. 'Black', 'Red', 'Neutral').
        diameter: Filament diameter in mm (default 1.75).
        spool_weight: Net filament weight per spool in grams (default 1000).
        empty_spool_weight: Empty spool weight in grams.
        nozzle_temp_min: Minimum nozzle temperature in Celsius.
        nozzle_temp_max: Maximum nozzle temperature in Celsius.
        bed_temp_min: Minimum bed temperature in Celsius.
        bed_temp_max: Maximum bed temperature in Celsius.
        density: Filament density in g/cm3 (e.g. 1.24 for PLA).
        price_per_spool: Price per spool.
        vendor: Vendor name (will be created if new).
        vendor_link: URL to vendor product page.
        notes: Free-text notes.
        features: List of feature names (e.g. ['Matte', 'High Speed']). Created if new.
    """
    try:
        payload: dict = {"name": name, "is_generic": is_generic}
        if brand:
            payload["brand"] = {"name": brand}
        if base_material_id is not None:
            payload["base_material_id"] = base_material_id
        if colors is not None:
            payload["colors"] = colors
        if color_family:
            payload["color_family"] = color_family
        if diameter is not None:
            payload["diameter"] = diameter
        if spool_weight is not None:
            payload["spool_weight"] = spool_weight
        if empty_spool_weight is not None:
            payload["empty_spool_weight"] = empty_spool_weight
        if nozzle_temp_min is not None:
            payload["nozzle_temp_min"] = nozzle_temp_min
        if nozzle_temp_max is not None:
            payload["nozzle_temp_max"] = nozzle_temp_max
        if bed_temp_min is not None:
            payload["bed_temp_min"] = bed_temp_min
        if bed_temp_max is not None:
            payload["bed_temp_max"] = bed_temp_max
        if density is not None:
            payload["density"] = density
        if price_per_spool is not None:
            payload["price_per_spool"] = price_per_spool
        if vendor:
            payload["vendor"] = {"name": vendor}
        if vendor_link:
            payload["vendor_link"] = vendor_link
        if notes:
            payload["notes"] = notes
        if features:
            payload["features"] = [{"name": f} for f in features]

        data = await _get_client().post("/api/materials/", json=payload)
        kind = "generic material" if data.get("is_generic") else "material blueprint"
        return f"Created {kind} #{data['id']}: {data['name']}"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def list_spools(
    status: str | None = None,
    printer: int | None = None,
    color: str | None = None,
    is_archived: bool | None = None,
) -> str:
    """List filament spools with optional filtering.

    Args:
        status: Filter by status — 'new', 'opened', 'active', 'in_use', 'low', 'empty', 'archived'.
        printer: Filter by assigned printer ID.
        color: Filter by color name (fuzzy match).
        is_archived: If true, show only archived spools. If false, exclude archived.
    """
    try:
        params: dict = {}
        if status:
            params["status"] = status
        if printer is not None:
            params["printer"] = printer
        if color:
            params["color"] = color
        if is_archived is not None:
            params["is_archived"] = "true" if is_archived else "false"
        data = await _get_client().get("/api/filament-spools/", params=params)
        return fmt.format_spool_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def add_filament_spool(
    filament_type_id: int,
    quantity: int = 1,
    initial_weight: int = 1000,
    location: str | None = None,
    notes: str | None = None,
    price_paid: float | None = None,
) -> str:
    """Add new filament spool(s) linked to an existing material blueprint.

    Args:
        filament_type_id: ID of the material blueprint this spool uses.
        quantity: Number of identical spools to add (default 1).
        initial_weight: Net filament weight in grams (default 1000g / 1kg).
        location: Storage location name (will be created if new).
        notes: Free-text notes.
        price_paid: Price paid for this spool.
    """
    try:
        payload: dict = {
            "filament_type_id": filament_type_id,
            "quantity": quantity,
            "initial_weight": initial_weight,
            "current_weight": initial_weight,
        }
        if location:
            payload["location"] = {"name": location}
        if notes:
            payload["notes"] = notes
        if price_paid is not None:
            payload["price_paid"] = price_paid

        data = await _get_client().post("/api/filament-spools/", json=payload)
        return f"Created spool #{data['id']} (qty: {data.get('quantity', 1)})"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def quick_add_spool(
    standalone_name: str,
    quantity: int = 1,
    initial_weight: int = 1000,
    standalone_brand: str | None = None,
    standalone_material_type_id: int | None = None,
    standalone_colors: list[str] | None = None,
    standalone_color_family: str | None = None,
    location: str | None = None,
    notes: str | None = None,
    price_paid: float | None = None,
    standalone_nozzle_temp_min: int | None = None,
    standalone_nozzle_temp_max: int | None = None,
    standalone_bed_temp_min: int | None = None,
    standalone_bed_temp_max: int | None = None,
    standalone_density: float | None = None,
) -> str:
    """Quick-add a filament spool without a material blueprint. Use this when you just want to track a spool without setting up a full material blueprint first.

    Args:
        standalone_name: Name for this spool (e.g. 'eSun PLA+ Black').
        quantity: Number of identical spools to add (default 1).
        initial_weight: Net filament weight in grams (default 1000g / 1kg).
        standalone_brand: Brand name (will be created if new).
        standalone_material_type_id: ID of a generic material type (e.g. PLA, PETG). Use list_materials with material_type='generic' to find IDs.
        standalone_colors: List of color names (e.g. ['Black']).
        standalone_color_family: Color family for grouping (e.g. 'Black', 'Red').
        location: Storage location name (will be created if new).
        notes: Free-text notes.
        price_paid: Price paid for this spool.
        standalone_nozzle_temp_min: Min nozzle temp in Celsius.
        standalone_nozzle_temp_max: Max nozzle temp in Celsius.
        standalone_bed_temp_min: Min bed temp in Celsius.
        standalone_bed_temp_max: Max bed temp in Celsius.
        standalone_density: Filament density in g/cm3.
    """
    try:
        payload: dict = {
            "is_quick_add": True,
            "standalone_name": standalone_name,
            "quantity": quantity,
            "initial_weight": initial_weight,
            "current_weight": initial_weight,
        }
        if standalone_brand:
            payload["standalone_brand"] = {"name": standalone_brand}
        if standalone_material_type_id is not None:
            payload["standalone_material_type_id"] = standalone_material_type_id
        if standalone_colors is not None:
            payload["standalone_colors"] = standalone_colors
        if standalone_color_family:
            payload["standalone_color_family"] = standalone_color_family
        if location:
            payload["location"] = {"name": location}
        if notes:
            payload["notes"] = notes
        if price_paid is not None:
            payload["price_paid"] = price_paid
        if standalone_nozzle_temp_min is not None:
            payload["standalone_nozzle_temp_min"] = standalone_nozzle_temp_min
        if standalone_nozzle_temp_max is not None:
            payload["standalone_nozzle_temp_max"] = standalone_nozzle_temp_max
        if standalone_bed_temp_min is not None:
            payload["standalone_bed_temp_min"] = standalone_bed_temp_min
        if standalone_bed_temp_max is not None:
            payload["standalone_bed_temp_max"] = standalone_bed_temp_max
        if standalone_density is not None:
            payload["standalone_density"] = standalone_density

        data = await _get_client().post("/api/filament-spools/", json=payload)
        return f"Quick-added spool #{data['id']}: {standalone_name} (qty: {data.get('quantity', 1)})"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def update_spool_weight(spool_id: int, current_weight: int) -> str:
    """Update the current weight of an opened filament spool. Auto-updates status based on remaining weight.

    Args:
        spool_id: The ID of the spool to update.
        current_weight: The current net filament weight in grams.
    """
    try:
        data = await _get_client().post(
            f"/api/filament-spools/{spool_id}/update-weight/",
            json={"current_weight": current_weight},
        )
        return fmt.format_spool_detail(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def mark_spool_empty(spool_id: int) -> str:
    """Mark a filament spool as empty and clear its printer assignment.

    Args:
        spool_id: The ID of the spool to mark as empty.
    """
    try:
        data = await _get_client().post(f"/api/filament-spools/{spool_id}/mark-empty/")
        return f"Spool #{spool_id} marked as empty."
    except Exception as e:
        return _err(e)


@mcp.tool()
async def open_spool(
    spool_id: int,
    status: str = "opened",
    location_id: int | None = None,
    printer_id: int | None = None,
) -> str:
    """Open a spool from an unopened batch. Creates a new individual spool record.

    Args:
        spool_id: The ID of the unopened spool batch to open from.
        status: Status for the opened spool — 'opened' or 'in_use'.
        location_id: Optional location ID to assign the opened spool.
        printer_id: Optional printer ID to assign the opened spool.
    """
    try:
        spool_config: dict = {"status": status}
        if location_id is not None:
            spool_config["location_id"] = location_id
        if printer_id is not None:
            spool_config["printer_id"] = printer_id

        data = await _get_client().post(
            f"/api/filament-spools/{spool_id}/open-spool/",
            json={"spools_to_open": [spool_config]},
        )
        return data.get("message", f"Spool opened from batch #{spool_id}.")
    except Exception as e:
        return _err(e)


@mcp.tool()
async def archive_spools(spool_ids: list[int]) -> str:
    """Bulk archive empty spools.

    Args:
        spool_ids: List of spool IDs to archive (must have 'empty' status).
    """
    try:
        data = await _get_client().post(
            "/api/filament-spools/bulk-archive/",
            json={"spool_ids": spool_ids},
        )
        archived = data.get("archived_count", 0)
        errors = data.get("errors", [])
        msg = f"Archived {archived} spool(s)."
        if errors:
            msg += f" Errors: {'; '.join(errors)}"
        return msg
    except Exception as e:
        return _err(e)


@mcp.tool()
async def toggle_material_favorite(material_id: int) -> str:
    """Toggle the favorite status of a material blueprint (max 5 favorites).

    Args:
        material_id: The ID of the material blueprint.
    """
    try:
        data = await _get_client().post(f"/api/materials/{material_id}/toggle-favorite/")
        return f"Material #{material_id}: {data.get('status', 'toggled')}"
    except Exception as e:
        return _err(e)


# ===================================================================
# Tool Group 4: Printer Management
# ===================================================================

@mcp.tool()
async def list_printers(search: str = "", status: str | None = None) -> str:
    """List all printers with optional search and status filter.

    Args:
        search: Search by title, manufacturer, serial number, or notes.
        status: Filter by status (e.g. 'Active', 'Under Repair', 'Retired').
    """
    try:
        params: dict = {}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        data = await _get_client().get("/api/printers/", params=params)
        return fmt.format_printer_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_printer(printer_id: int) -> str:
    """Get full details on a specific printer including mods and assigned filament.

    Args:
        printer_id: The ID of the printer.
    """
    try:
        data = await _get_client().get(f"/api/printers/{printer_id}/")
        return fmt.format_printer_detail(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def update_printer(
    printer_id: int,
    title: str | None = None,
    status: str | None = None,
    serial_number: str | None = None,
    notes: str | None = None,
    purchase_price: float | None = None,
    maintenance_notes: str | None = None,
    manufacturer: str | None = None,
) -> str:
    """Update a printer record. Only the fields you provide will be changed.

    Args:
        printer_id: The ID of the printer to update.
        title: New title.
        status: New status (e.g. 'Active', 'Under Repair', 'Retired').
        serial_number: Serial number.
        notes: Free-text notes.
        purchase_price: Purchase price.
        maintenance_notes: Maintenance notes.
        manufacturer: Manufacturer/brand name (will be created if new).
    """
    try:
        payload: dict = {}
        if title is not None:
            payload["title"] = title
        if status is not None:
            payload["status"] = status
        if serial_number is not None:
            payload["serial_number"] = serial_number
        if notes is not None:
            payload["notes"] = notes
        if purchase_price is not None:
            payload["purchase_price"] = purchase_price
        if maintenance_notes is not None:
            payload["maintenance_notes"] = maintenance_notes
        if manufacturer is not None:
            payload["manufacturer"] = {"name": manufacturer}

        data = await _get_client().patch(f"/api/printers/{printer_id}/", json=payload)
        return f"Updated printer #{data['id']}: {data['title']} (status: {data.get('status', '?')})"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def add_mod(
    printer: int,
    name: str,
    link: str | None = None,
    status: str = "Planned",
) -> str:
    """Add a mod/upgrade to a printer.

    Args:
        printer: The ID of the printer to add the mod to.
        name: Name of the mod.
        link: URL to the mod (Printables, GitHub, etc.).
        status: Mod status — 'Planned', 'In Progress', 'Completed'.
    """
    try:
        payload: dict = {"printer": printer, "name": name, "status": status}
        if link:
            payload["link"] = link
        data = await _get_client().post("/api/mods/", json=payload)
        return f"Added mod #{data['id']}: {data['name']} to printer #{printer}"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def update_mod(
    mod_id: int,
    name: str | None = None,
    link: str | None = None,
    status: str | None = None,
) -> str:
    """Update a printer mod. Only the fields you provide will be changed.

    Args:
        mod_id: The ID of the mod to update.
        name: New name for the mod.
        link: URL to the mod.
        status: New status — 'Planned', 'In Progress', 'Completed'.
    """
    try:
        payload: dict = {}
        if name is not None:
            payload["name"] = name
        if link is not None:
            payload["link"] = link
        if status is not None:
            payload["status"] = status

        data = await _get_client().patch(f"/api/mods/{mod_id}/", json=payload)
        return f"Updated mod #{data['id']}: {data['name']} [{data.get('status', '?')}]"
    except Exception as e:
        return _err(e)


# ===================================================================
# Tool Group 5: Project Management
# ===================================================================

@mcp.tool()
async def list_projects(search: str = "", status: str | None = None) -> str:
    """List projects with optional search and status filter.

    Args:
        search: Search by project name, description, status, or notes.
        status: Filter by status — 'Planning', 'In Progress', 'On Hold', 'Completed', 'Canceled'.
    """
    try:
        params: dict = {}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        data = await _get_client().get("/api/projects/", params=params)
        return fmt.format_project_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_project(project_id: int) -> str:
    """Get full project details including BOM, linked inventory, printers, trackers, and files.

    Args:
        project_id: The ID of the project.
    """
    try:
        data = await _get_client().get(f"/api/projects/{project_id}/")
        return fmt.format_project_detail(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def create_project(
    project_name: str,
    description: str | None = None,
    status: str = "Planning",
    start_date: str | None = None,
    due_date: str | None = None,
    notes: str | None = None,
) -> str:
    """Create a new project.

    Args:
        project_name: Name of the project.
        description: Project description.
        status: Initial status — 'Planning', 'In Progress', 'On Hold'.
        start_date: Start date in YYYY-MM-DD format.
        due_date: Due date in YYYY-MM-DD format.
        notes: Free-text notes.
    """
    try:
        payload: dict = {"project_name": project_name, "status": status}
        if description:
            payload["description"] = description
        if start_date:
            payload["start_date"] = start_date
        if due_date:
            payload["due_date"] = due_date
        if notes:
            payload["notes"] = notes

        data = await _get_client().post("/api/projects/", json=payload)
        return f"Created project #{data['id']}: {data['project_name']} [{data['status']}]"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def update_project(
    project_id: int,
    project_name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
    notes: str | None = None,
) -> str:
    """Update a project. Only the fields you provide will be changed.

    Args:
        project_id: The ID of the project to update.
        project_name: New project name.
        description: New description.
        status: New status — 'Planning', 'In Progress', 'On Hold', 'Completed', 'Canceled'.
        start_date: Start date in YYYY-MM-DD format.
        due_date: Due date in YYYY-MM-DD format.
        notes: Free-text notes.
    """
    try:
        payload: dict = {}
        if project_name is not None:
            payload["project_name"] = project_name
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        if start_date is not None:
            payload["start_date"] = start_date
        if due_date is not None:
            payload["due_date"] = due_date
        if notes is not None:
            payload["notes"] = notes

        data = await _get_client().patch(f"/api/projects/{project_id}/", json=payload)
        return f"Updated project #{data['id']}: {data['project_name']} [{data['status']}]"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def add_bom_item(
    project: int,
    description: str,
    quantity_needed: int = 1,
    inventory_item: int | None = None,
    status: str = "unlinked",
    notes: str | None = None,
) -> str:
    """Add a Bill of Materials line item to a project. If linked to an inventory item, it reserves stock.

    Args:
        project: The ID of the project.
        description: Description of the BOM item (e.g. "M3x8 SHCS").
        quantity_needed: Quantity needed.
        inventory_item: Optional ID of an existing inventory item to link (reserves stock).
        status: BOM status — 'linked' (auto-reserves), 'unlinked', or 'needs_purchase'.
        notes: Free-text notes.
    """
    try:
        payload: dict = {
            "project": project,
            "description": description,
            "quantity_needed": quantity_needed,
            "status": status,
        }
        if inventory_item is not None:
            payload["inventory_item"] = inventory_item
        if notes:
            payload["notes"] = notes

        data = await _get_client().post("/api/projectbomitems/", json=payload)
        return f"Added BOM item #{data['id']}: {data.get('description', '?')} × {data.get('quantity_needed', '?')}"
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_shopping_list() -> str:
    """Get the consolidated shopping list — items that need to be purchased across all active projects."""
    try:
        data = await _get_client().get("/api/projectbomitems/shopping_list/")
        return fmt.format_shopping_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def link_printer_to_project(project: int, printer: int) -> str:
    """Associate a printer with a project.

    Args:
        project: The project ID.
        printer: The printer ID.
    """
    try:
        data = await _get_client().post(
            "/api/projectprinters/",
            json={"project": project, "printer": printer},
        )
        return f"Linked printer #{printer} to project #{project}."
    except Exception as e:
        return _err(e)


# ===================================================================
# Tool Group 6: Print Tracker
# ===================================================================

@mcp.tool()
async def list_trackers(search: str = "") -> str:
    """List all print trackers with optional search.

    Args:
        search: Search by tracker name or GitHub URL.
    """
    try:
        params: dict = {}
        if search:
            params["search"] = search
        data = await _get_client().get("/api/trackers/", params=params)
        return fmt.format_tracker_list(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def get_tracker(tracker_id: int) -> str:
    """Get full tracker details including file list and progress.

    Args:
        tracker_id: The ID of the tracker.
    """
    try:
        data = await _get_client().get(f"/api/trackers/{tracker_id}/")
        return fmt.format_tracker_detail(data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def create_tracker_from_github(github_url: str) -> str:
    """Crawl a GitHub repository for printable files and return the results. Use this to preview files before creating a tracker.

    Args:
        github_url: Full GitHub URL to a repository or subdirectory (e.g. https://github.com/VoronDesign/Voron-0/tree/main/STLs).
    """
    try:
        data = await _get_client().post(
            "/api/trackers/crawl-github/",
            json={"github_url": github_url},
        )
        if data.get("success") is False:
            return f"GitHub crawl failed: {data.get('error', 'unknown error')}"
        files = data.get("files", [])
        return f"Found {len(files)} printable file(s) from {github_url}."
    except Exception as e:
        return _err(e)


@mcp.tool()
async def update_file_status(
    file_id: int,
    status: str | None = None,
    printed_quantity: int | None = None,
) -> str:
    """Update the print status or printed quantity of a tracker file.

    Args:
        file_id: The ID of the tracker file.
        status: New status for the file.
        printed_quantity: Number of copies printed so far.
    """
    try:
        payload: dict = {}
        if status is not None:
            payload["status"] = status
        if printed_quantity is not None:
            payload["printed_quantity"] = printed_quantity

        data = await _get_client().patch(
            f"/api/tracker-files/{file_id}/update_status/",
            json=payload,
        )
        return (
            f"Updated file #{file_id}: {data.get('filename', '?')} "
            f"— {data.get('printed_quantity', '?')}/{data.get('quantity', '?')} "
            f"[{data.get('status', '?')}]"
        )
    except Exception as e:
        return _err(e)


# ===================================================================
# Tool Group 7: Reference Data (Brands, Locations, Part Types, Vendors)
# ===================================================================

@mcp.tool()
async def list_brands() -> str:
    """List all brands/manufacturers in the system."""
    try:
        data = await _get_client().get("/api/brands/")
        if not data:
            return "No brands found."
        return "Brands: " + ", ".join(f"[{b['id']}] {b['name']}" for b in data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def list_locations() -> str:
    """List all storage locations in the system."""
    try:
        data = await _get_client().get("/api/locations/")
        if not data:
            return "No locations found."
        return "Locations: " + ", ".join(f"[{l['id']}] {l['name']}" for l in data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def list_part_types() -> str:
    """List all part types/categories in the system."""
    try:
        data = await _get_client().get("/api/parttypes/")
        if not data:
            return "No part types found."
        return "Part Types: " + ", ".join(f"[{p['id']}] {p['name']}" for p in data)
    except Exception as e:
        return _err(e)


@mcp.tool()
async def list_vendors() -> str:
    """List all vendors/suppliers in the system."""
    try:
        data = await _get_client().get("/api/vendors/")
        if not data:
            return "No vendors found."
        return "Vendors: " + ", ".join(f"[{v['id']}] {v['name']}" for v in data)
    except Exception as e:
        return _err(e)
