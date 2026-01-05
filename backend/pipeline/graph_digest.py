"""
Knowledge Graph Digest Generator for PM Models.

This module creates actionable summaries from weekly macro knowledge graphs
to provide PM models with focused, directional insights.
"""

from typing import Dict, Any, List


def make_digest(weekly_graph: dict) -> dict:
    """
    Create a structured digest from a weekly knowledge graph.
    
    This digest focuses on actionable insights:
    - Top 10 market edges sorted by (strength * confidence) descending
    - For each tradable asset, creates a 2-hop neighborhood summary
    - Filters out weak edges (strength * confidence <= 0.3)
    
    Args:
        weekly_graph: Full knowledge graph with nodes and edges
        
    Returns:
        Structured digest dict with:
        - week_id: Week identifier
        - asof_et: As-of timestamp
        - top_edges: List of top 10 edges with full metadata
        - asset_subgraphs: Dict keyed by asset ticker, each with:
            - direct_drivers: EVENT/NARRATIVE nodes pointing to asset
            - indirect_influences: Nodes 2 hops away
            - setup_signals: INDICATOR nodes
            - strength_score: Average of incoming edge strengths
        - notes: List of summary notes
    """
    # Extract metadata
    week_id = weekly_graph.get("week_id", "")
    asof_et = weekly_graph.get("asof_et", "")
    nodes = weekly_graph.get("nodes", [])
    edges = weekly_graph.get("edges", [])
    
    # Build node lookup for fast access
    node_by_id = {node["id"]: node for node in nodes}
    
    # Filter and sort edges by impact score
    MIN_THRESHOLD = 0.3
    scored_edges = []
    
    for edge in edges:
        strength = edge.get("strength", 0)
        confidence = edge.get("confidence", 0)
        impact_score = strength * confidence
        
        if impact_score > MIN_THRESHOLD:
            scored_edges.append({
                "edge": edge,
                "impact_score": impact_score
            })
    
    # Sort by impact score descending
    scored_edges.sort(key=lambda x: x["impact_score"], reverse=True)
    
    # Take top 10 edges
    top_10 = scored_edges[:10]
    top_edges = []
    
    for item in top_10:
        edge = item["edge"]
        source_node = node_by_id.get(edge["source"], {})
        target_node = node_by_id.get(edge["target"], {})
        
        top_edges.append({
            "source_id": edge["source"],
            "source_type": source_node.get("type", "UNKNOWN"),
            "source_label": source_node.get("label", ""),
            "target_id": edge["target"],
            "target_type": target_node.get("type", "UNKNOWN"),
            "target_label": target_node.get("label", ""),
            "relation": edge.get("relation", ""),
            "sign": edge.get("sign", "0"),
            "strength": edge.get("strength", 0),
            "confidence": edge.get("confidence", 0),
            "impact_score": item["impact_score"],
            "time_window": edge.get("time_window", ""),
            "evidence": edge.get("evidence", []),
            "condition": edge.get("condition", "")
        })
    
    # Build asset subgraphs for tradable universe
    TRADABLE_ASSETS = ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"]
    asset_subgraphs = {}
    
    for ticker in TRADABLE_ASSETS:
        asset_id = f"ast:{ticker}"
        
        if asset_id not in node_by_id:
            continue
        
        # Find all edges pointing to this asset
        incoming_edges = [e for e in edges if e["target"] == asset_id]
        
        # Calculate average strength score
        if incoming_edges:
            strength_score = sum(e.get("strength", 0) for e in incoming_edges) / len(incoming_edges)
        else:
            strength_score = 0.0
        
        # Categorize direct drivers
        direct_drivers = []
        setup_signals = []
        
        for edge in incoming_edges:
            source_node = node_by_id.get(edge["source"], {})
            source_type = source_node.get("type", "")
            
            strength = edge.get("strength", 0)
            confidence = edge.get("confidence", 0)
            impact = strength * confidence
            
            # Only include edges above threshold
            if impact <= MIN_THRESHOLD:
                continue
            
            driver_info = {
                "node_id": edge["source"],
                "type": source_type,
                "label": source_node.get("label", ""),
                "relation": edge.get("relation", ""),
                "sign": edge.get("sign", "0"),
                "strength": strength,
                "confidence": confidence,
                "impact_score": impact,
                "evidence": edge.get("evidence", []),
                "condition": edge.get("condition", "")
            }
            
            if source_type in ["EVENT", "NARRATIVE", "SCENARIO"]:
                direct_drivers.append(driver_info)
            elif source_type == "INDICATOR":
                setup_signals.append(driver_info)
        
        # Sort direct drivers by impact score
        direct_drivers.sort(key=lambda x: x["impact_score"], reverse=True)
        
        # Limit to top 3 direct drivers
        direct_drivers = direct_drivers[:3]
        
        # Find 2-hop influences (nodes that connect to direct drivers)
        indirect_influences = []
        
        for driver in direct_drivers:
            driver_id = driver["node_id"]
            
            # Find edges pointing to this driver
            second_hop_edges = [e for e in edges if e["target"] == driver_id]
            
            for edge in second_hop_edges:
                source_node = node_by_id.get(edge["source"], {})
                
                strength = edge.get("strength", 0)
                confidence = edge.get("confidence", 0)
                impact = strength * confidence
                
                if impact <= MIN_THRESHOLD:
                    continue
                
                indirect_influences.append({
                    "node_id": edge["source"],
                    "type": source_node.get("type", ""),
                    "label": source_node.get("label", ""),
                    "via": driver["label"],
                    "relation": edge.get("relation", ""),
                    "impact_score": impact
                })
        
        # Sort and deduplicate indirect influences
        indirect_influences.sort(key=lambda x: x["impact_score"], reverse=True)
        
        # Remove duplicates (same node_id)
        seen_nodes = set()
        unique_indirect = []
        for inf in indirect_influences:
            if inf["node_id"] not in seen_nodes:
                seen_nodes.add(inf["node_id"])
                unique_indirect.append(inf)
        
        # Limit to top 5 indirect influences
        indirect_influences = unique_indirect[:5]
        
        # Get strongest evidence
        strongest_evidence = ""
        if direct_drivers:
            top_driver = direct_drivers[0]
            evidence_list = top_driver.get("evidence", [])
            if evidence_list:
                strongest_evidence = evidence_list[0]
        
        asset_subgraphs[ticker] = {
            "direct_drivers": direct_drivers,
            "indirect_influences": indirect_influences,
            "setup_signals": setup_signals,
            "strength_score": round(strength_score, 3),
            "strongest_evidence": strongest_evidence
        }
    
    # Generate summary notes
    notes = []
    notes.append(f"Digest generated from {len(nodes)} nodes and {len(edges)} edges")
    notes.append(f"Filtered to {len(scored_edges)} edges above threshold (strength * confidence > {MIN_THRESHOLD})")
    notes.append(f"Top 10 edges represent the strongest market drivers this week")
    
    # Count assets with drivers
    assets_with_drivers = sum(1 for sg in asset_subgraphs.values() if sg["direct_drivers"])
    notes.append(f"{assets_with_drivers} of {len(TRADABLE_ASSETS)} assets have identifiable drivers")
    
    return {
        "week_id": week_id,
        "asof_et": asof_et,
        "top_edges": top_edges,
        "asset_subgraphs": asset_subgraphs,
        "notes": notes
    }
