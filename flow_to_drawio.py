"""
flow_to_drawio.py

Converts a Langflow flow_structure.json to a draw.io compatible XML file (.drawio).

Usage:
    python flow_to_drawio.py                          # uses flow_structure.json -> flow_structure.drawio
    python flow_to_drawio.py input.json               # uses input.json -> input.drawio
    python flow_to_drawio.py input.json output.drawio # explicit input and output paths
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

# ---------------------------------------------------------------------------
# draw.io style constants
# ---------------------------------------------------------------------------

# Node styles per Langflow component type (fallback to DEFAULT_NODE_STYLE)
COMPONENT_STYLES: dict[str, str] = {
    "ChatInput": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
        "fontStyle=1;fontSize=12;"
    ),
    "ChatOutput": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;"
        "fontStyle=1;fontSize=12;"
    ),
    "TextInput": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;"
        "fontSize=11;"
    ),
    "OpenAIModel": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;"
        "fontStyle=1;fontSize=12;"
    ),
    "Prompt": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;"
        "fontSize=12;"
    ),
}

DEFAULT_NODE_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;"
    "fontColor=#333333;fontSize=11;"
)

EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
    "jettySize=auto;exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
    "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
)

# Default node dimensions (draw.io units)
NODE_WIDTH = 180
NODE_HEIGHT = 60

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def prettify(element: ET.Element) -> str:
    """Return a pretty-printed XML string for an ElementTree Element."""
    raw = ET.tostring(element, encoding="unicode")
    reparsed = minidom.parseString(raw)
    return reparsed.toprettyxml(indent="  ", encoding=None)  # type: ignore[return-value]


def node_label(node_data: dict) -> str:
    """Build the label shown inside a draw.io cell for a Langflow node."""
    node_info = node_data.get("node", {})
    display_name = node_info.get("display_name") or node_data.get("type", "Unknown")
    component_type = node_data.get("type", "")
    if component_type and component_type != display_name:
        return f"<b>{display_name}</b><br/><i style='font-size:10px'>{component_type}</i>"
    return f"<b>{display_name}</b>"


def node_style(component_type: str) -> str:
    """Return the draw.io style string for a given Langflow component type."""
    return COMPONENT_STYLES.get(component_type, DEFAULT_NODE_STYLE)


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------


def convert(flow: dict) -> ET.Element:
    """Convert a parsed Langflow flow dict to an mxGraphModel ElementTree."""

    flow_data = flow.get("data", {})
    nodes: list[dict] = flow_data.get("nodes", [])
    edges: list[dict] = flow_data.get("edges", [])

    # Root elements required by draw.io
    graph_model = ET.Element(
        "mxGraphModel",
        attrib={
            "dx": "1422",
            "dy": "762",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": "1169",
            "pageHeight": "827",
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(graph_model, "root")

    # draw.io requires cells with id="0" and id="1" as anchors
    ET.SubElement(root, "mxCell", attrib={"id": "0"})
    ET.SubElement(root, "mxCell", attrib={"id": "1", "parent": "0"})

    # --- nodes ----------------------------------------------------------------
    for node in nodes:
        node_id: str = node.get("id", "")
        position: dict = node.get("position", {})
        node_data: dict = node.get("data", {})
        component_type: str = node_data.get("type", "")

        x = str(int(position.get("x", 0)))
        y = str(int(position.get("y", 0)))

        cell = ET.SubElement(
            root,
            "mxCell",
            attrib={
                "id": node_id,
                "value": node_label(node_data),
                "style": node_style(component_type),
                "vertex": "1",
                "parent": "1",
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            attrib={
                "x": x,
                "y": y,
                "width": str(NODE_WIDTH),
                "height": str(NODE_HEIGHT),
                "as": "geometry",
            },
        )

    # --- edges ----------------------------------------------------------------
    for edge in edges:
        edge_id: str = edge.get("id", "")
        source: str = edge.get("source", "")
        target: str = edge.get("target", "")
        source_handle: str = edge.get("sourceHandle", "")
        target_handle: str = edge.get("targetHandle", "")

        # Build tooltip showing handle names
        tooltip = ""
        if source_handle or target_handle:
            tooltip = f"{source_handle} → {target_handle}"

        cell = ET.SubElement(
            root,
            "mxCell",
            attrib={
                "id": edge_id,
                "value": tooltip,
                "style": EDGE_STYLE,
                "edge": "1",
                "source": source,
                "target": target,
                "parent": "1",
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            attrib={"relative": "1", "as": "geometry"},
        )

    return graph_model


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = sys.argv[1:]

    # Resolve input path
    if len(args) >= 1:
        input_path = Path(args[0])
    else:
        input_path = Path("flow_structure.json")

    # Resolve output path
    if len(args) >= 2:
        output_path = Path(args[1])
    else:
        output_path = input_path.with_suffix(".drawio")

    if not input_path.exists():
        print(f"Error: input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    # Load flow JSON
    with input_path.open(encoding="utf-8") as fh:
        flow = json.load(fh)

    # Convert
    graph_model = convert(flow)

    # Write draw.io XML
    xml_str = prettify(graph_model)
    # minidom adds an XML declaration; draw.io expects it so keep it.
    output_path.write_text(xml_str, encoding="utf-8")

    node_count = len(flow.get("data", {}).get("nodes", []))
    edge_count = len(flow.get("data", {}).get("edges", []))
    print(f"Converted '{input_path}' -> '{output_path}'")
    print(f"  Nodes : {node_count}")
    print(f"  Edges : {edge_count}")
    print(f"\nOpen '{output_path}' in https://app.diagrams.net (draw.io) to view the diagram.")


if __name__ == "__main__":
    main()
