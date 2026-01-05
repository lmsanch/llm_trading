"""Graph extractor module for pipeline integration."""

from __future__ import annotations

import json
import re
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"]

IMPACT_STRENGTH = {"CRITICAL": 0.9, "HIGH": 0.7, "MEDIUM": 0.5, "LOW": 0.3}

def slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:60] if s else "x"

def stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}:{h}"

def parse_date_yyyymmdd(date_str: str) -> str:
    # expects YYYY-MM-DD
    return date_str.replace("-", "")

def coerce_asof(research: Dict[str, Any]) -> str:
    # Try common fields; fallback now
    for k in ["asof_et", "asof", "timestamp", "as_of"]:
        v = research.get(k)
        if isinstance(v, str) and v:
            return v
    return datetime.now().isoformat()

def map_expected_to_sign(expected: str) -> str:
    e = (expected or "").upper()
    if any(x in e for x in ["STRONG", "OUTPERFORM", "POSITIVE", "SPIKE"]):
        return "+"
    if any(x in e for x in ["NEGATIVE", "UNDERPERFORM", "SIGNIFICANT", "CRUSH"]):
        return "-"
    if any(x in e for x in ["FLAT", "RANGE"]):
        return "0"
    return "0"

@dataclass
class Node:
    id: str
    type: str
    label: str
    week_id: Optional[str] = None
    tags: Optional[List[str]] = None
    payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {"id": self.id, "type": self.type, "label": self.label}
        if self.week_id: out["week_id"] = self.week_id
        if self.tags: out["tags"] = self.tags
        if self.payload: out["payload"] = self.payload
        return out

@dataclass
class Edge:
    id: str
    source: str
    target: str
    relation: str
    time_window: str = "7D"
    sign: str = "0"
    strength: Optional[float] = None
    confidence: Optional[float] = None
    condition: Optional[str] = None
    evidence: Optional[List[str]] = None
    edge_tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "time_window": self.time_window
        }
        if self.sign is not None: out["sign"] = self.sign
        if self.strength is not None: out["strength"] = float(self.strength)
        if self.confidence is not None: out["confidence"] = float(self.confidence)
        if self.condition: out["condition"] = self.condition[:240]
        if self.evidence: out["evidence"] = [x[:240] for x in self.evidence][:10]
        if self.edge_tags: out["edge_tags"] = [x[:40] for x in self.edge_tags][:20]
        return out

class GraphBuilder:
    def __init__(self, week_id: str, asof_et: str):
        self.week_id = week_id
        self.asof_et = asof_et
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}

    def add_node(self, node: Node) -> None:
        if node.id not in self.nodes:
            self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.id not in self.edges:
            self.edges[edge.id] = edge

    def ensure_asset_nodes(self) -> None:
        for t in UNIVERSE:
            self.add_node(Node(id=f"ast:{t}", type="ASSET", label=t, week_id=self.week_id, tags=["universe"], payload={"ticker": t}))

def extract_graph(research: Dict[str, Any]) -> Dict[str, Any]:
    # Extract from structured_json if present (common pattern in backend)
    data = research.get("structured_json", research)
    
    # Try to find date info in various places
    week_id = research.get("week_id") or data.get("week_id") or "0000-00-00"
    asof_et = research.get("generated_at") or coerce_asof(research)

    gb = GraphBuilder(week_id=week_id, asof_et=asof_et)
    gb.ensure_asset_nodes()

    # --- Events
    events = data.get("event_calendar") or data.get("event_calendar_next_7d") or []
    for ev in events:
        date_et = ev.get("date_et") or ev.get("date") or ""
        event_name = ev.get("event") or "Event"
        ev_id = f"evt:{parse_date_yyyymmdd(date_et)}_{slug(event_name)}" if date_et else stable_id("evt", event_name)
        gb.add_node(Node(
            id=ev_id,
            type="EVENT",
            label=event_name[:140],
            week_id=week_id,
            tags=["event"],
            payload={"date_et": date_et, "impact": ev.get("impact")}
        ))
        affected = ev.get("affected_assets") or ev.get("affected") or []
        for a in affected:
            if a in UNIVERSE:
                eid = stable_id("e", ev_id, f"ast:{a}", "CATALYST_FOR")
                gb.add_edge(Edge(
                    id=eid,
                    source=ev_id,
                    target=f"ast:{a}",
                    relation="CATALYST_FOR",
                    time_window="EVENT",
                    sign="0",
                    strength=IMPACT_STRENGTH.get((ev.get("impact") or "MEDIUM").upper(), 0.5),
                    confidence=0.65,
                    evidence=[ev.get("why_matters_this_week") or ev.get("expected_outcome") or ""]
                ))

    # --- Narratives
    narratives = data.get("top_narratives") or []
    for nar in narratives:
        # accept either object or string list
        if isinstance(nar, str):
            name = nar
            why = []
            fals = []
        else:
            name = nar.get("name") or "Narrative"
            why = nar.get("why_this_week") or []
            fals = nar.get("falsifiers_this_week") or []
        nar_id = f"nar:{slug(name)}"
        gb.add_node(Node(id=nar_id, type="NARRATIVE", label=name[:140], week_id=week_id, tags=["narrative"], payload={"why": why, "falsifiers": fals}))

        # link narratives to events if keyword overlap (simple deterministic)
        for ev in events:
            ev_name = (ev.get("event") or "").lower()
            if isinstance(name, str) and any(k in ev_name for k in [w for w in slug(name).split("_") if len(w) >= 4]):
                date_et = ev.get("date_et") or ev.get("date") or ""
                ev_id_guess = f"evt:{parse_date_yyyymmdd(date_et)}_{slug(ev.get('event','Event'))}" if date_et else stable_id("evt", ev.get("event","Event"))
                if ev_id_guess in gb.nodes:
                    eid = stable_id("e", ev_id_guess, nar_id, "SUPPORTS")
                    gb.add_edge(Edge(
                        id=eid, source=ev_id_guess, target=nar_id, relation="SUPPORTS",
                        time_window="7D", sign="0", strength=0.6, confidence=0.55,
                        evidence=[f"Keyword overlap: {name} ~ {ev.get('event','')}"]
                    ))

        # link narratives to assets via explicit ticker scan in text
        text_blob = json.dumps(nar) if not isinstance(nar, str) else nar
        mentioned = [t for t in UNIVERSE if t in text_blob]
        for t in mentioned:
            eid = stable_id("e", nar_id, f"ast:{t}", "INFLUENCES")
            gb.add_edge(Edge(
                id=eid, source=nar_id, target=f"ast:{t}", relation="INFLUENCES",
                time_window="7D", sign="0", strength=0.5, confidence=0.55,
                evidence=[name[:200]]
            ))

    # --- Indicators + scenario edges from asset_setups
    # Support both old key 'tradable_candidates' and new 'asset_setups'
    setups = data.get("asset_setups") or data.get("tradable_candidates") or []
    for s in setups:
        ticker = s.get("ticker")
        if ticker not in UNIVERSE:
            continue

        # Indicators
        for wi in (s.get("watch_indicators") or []):
            ind_name = wi.get("name") or "indicator"
            ind_id = f"ind:{slug(ind_name)}"
            gb.add_node(Node(
                id=ind_id, type="INDICATOR", label=ind_name[:140], week_id=week_id,
                tags=["indicator"], payload={"type": wi.get("type"), "check_frequency": wi.get("check_frequency")}
            ))
            eid = stable_id("e", ind_id, f"ast:{ticker}", "DRIVES")
            gb.add_edge(Edge(
                id=eid, source=ind_id, target=f"ast:{ticker}", relation="DRIVES",
                time_window=wi.get("check_frequency") or "7D",
                sign="0", strength=0.6, confidence=0.6,
                evidence=[f"bullish: {wi.get('bullish_condition','')}", f"bearish: {wi.get('bearish_condition','')}"]
            ))

        # Scenarios
        for j, sc in enumerate(s.get("scenario_map") or []):
            cond = sc.get("if") or sc.get("condition") or ""
            label = sc.get("label") or f"{ticker} scenario {j+1}"
            expected = sc.get("expected_vs_spy") or sc.get("expected") or ""
            sign = map_expected_to_sign(expected)

            scn_id = stable_id("scn", ticker, cond, label)
            gb.add_node(Node(
                id=scn_id, type="SCENARIO", label=label[:140], week_id=week_id,
                tags=["scenario"], payload={"if": cond, "expected_vs_spy": expected}
            ))

            # scenario -> asset
            eid = stable_id("e", scn_id, f"ast:{ticker}", "DRIVES")
            gb.add_edge(Edge(
                id=eid, source=scn_id, target=f"ast:{ticker}", relation="DRIVES",
                time_window="7D", sign=sign, strength=0.7, confidence=0.6,
                condition=(cond[:240] if cond else None),
                evidence=[f"expected_vs_spy: {expected}", f"magnitude: {sc.get('magnitude','')}"]
            ))

    # --- Named entities (optional but nice for D3)
    ne = data.get("named_entities") or {}
    for cat, items in ne.items():
        if not isinstance(items, list):
            continue
        for it in items[:100]:
            label = str(it)
            ent_id = f"ent:{slug(label)}"
            gb.add_node(Node(
                id=ent_id, type="ENTITY", label=label[:140], week_id=week_id,
                tags=["entity", str(cat)[:40]], payload={"category": cat}
            ))
            # lightweight link to narrative cluster if mentioned
            for nar in narratives:
                blob = json.dumps(nar) if not isinstance(nar, str) else nar
                if label and label in blob:
                    nar_id = f"nar:{slug(nar if isinstance(nar,str) else nar.get('name','Narrative'))}"
                    if nar_id in gb.nodes:
                        eid = stable_id("e", ent_id, nar_id, "EVIDENCES")
                        gb.add_edge(Edge(
                            id=eid, source=ent_id, target=nar_id, relation="EVIDENCES",
                            time_window="7D", sign="0", strength=0.3, confidence=0.5,
                            evidence=[f"entity mentioned in narrative: {label}"]
                        ))

    return {
        "week_id": gb.week_id,
        "asof_et": gb.asof_et,
        "meta": {"universe": UNIVERSE},
        "nodes": [n.to_dict() for n in gb.nodes.values()],
        "edges": [e.to_dict() for e in gb.edges.values()]
    }
