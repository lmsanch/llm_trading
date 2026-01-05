import React, { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";

const TYPE_ORDER = ["ASSET", "EVENT", "INDICATOR", "NARRATIVE", "SCENARIO", "ENTITY"];

function edgeScore(e) {
    const s = e.strength ?? 0.4;
    const c = e.confidence ?? 0.4;
    return s * c;
}

export default function WeeklyGraphViewer({ src, data, digest }) {
    const ref = useRef(null);
    const [graph, setGraph] = useState(null);
    const [typeFilter, setTypeFilter] = useState({
        ASSET: true,
        EVENT: true,
        INDICATOR: true,
        NARRATIVE: true,
        ENTITY: false,
        SCENARIO: true
    });
    const [minEdgeScore, setMinEdgeScore] = useState(0.12);
    const [focusNodeId, setFocusNodeId] = useState("");

    useEffect(() => {
        if (graph) return;
        if (src) {
            fetch(src).then(r => r.json()).then(setGraph).catch(console.error);
        }
    }, [src, graph]);

    useEffect(() => {
        if (typeof data !== 'undefined') {
            setGraph(data);
        }
    }, [data]);

    useEffect(() => {
        if (typeof digest !== 'undefined') {
            setGraph(digest);
        }
    }, [digest]);

    const filtered = useMemo(() => {
        if (!graph) return null;

        const allowedNodeIds = new Set(
            graph.nodes.filter(n => typeFilter[n.type]).map(n => n.id)
        );

        // filter edges by score + node allowlist
        const edges = graph.edges
            .filter(e => edgeScore(e) >= minEdgeScore)
            .filter(e => allowedNodeIds.has(String(e.source)) && allowedNodeIds.has(String(e.target)));

        // if focusNodeId is set, keep 2-hop neighborhood
        if (focusNodeId) {
            const hop1 = new Set();
            edges.forEach(e => {
                if (e.source === focusNodeId || e.target === focusNodeId) {
                    hop1.add(String(e.source));
                    hop1.add(String(e.target));
                }
            });
            const hop2 = new Set(hop1);
            edges.forEach(e => {
                if (hop1.has(String(e.source)) || hop1.has(String(e.target))) {
                    hop2.add(String(e.source));
                    hop2.add(String(e.target));
                }
            });
            const edges2 = edges.filter(e => hop2.has(String(e.source)) && hop2.has(String(e.target)));
            const nodes2 = graph.nodes.filter(n => hop2.has(n.id));
            return { ...graph, nodes: nodes2, edges: edges2 };
        }

        // nodes referenced by remaining edges
        const used = new Set();
        edges.forEach(e => {
            used.add(String(e.source));
            used.add(String(e.target));
        });
        const nodes = graph.nodes.filter(n => used.has(n.id));

        return { ...graph, nodes, edges };
    }, [graph, typeFilter, minEdgeScore, focusNodeId]);

    useEffect(() => {
        if (!filtered || !ref.current) return;

        const svg = d3.select(ref.current);
        svg.selectAll("*").remove();

        const width = ref.current.clientWidth || 1000;
        const height = ref.current.clientHeight || 700;

        // Deep copy to prevent d3 from mutating state directly
        const nodes = filtered.nodes.map(n => ({ ...n }));
        const links = filtered.edges.map(e => ({ ...e }));

        const defs = svg.append("defs");
        defs.append("marker")
            .attr("id", "arrow")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 18)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("fill", "#f97316") // Orange arrow
            .attr("d", "M0,-5L10,0L0,5");

        const g = svg.append("g");

        const zoom = d3.zoom()
            .scaleExtent([0.2, 4])
            .on("zoom", (event) => g.attr("transform", event.transform.toString()));
        svg.call(zoom);

        const link = g.append("g")
            .attr("stroke-opacity", 0.6)
            .selectAll("line")
            .data(links)
            .enter()
            .append("line")
            .attr("stroke-width", (d) => 1 + 6 * (d.strength ?? 0.4))
            .attr("marker-end", "url(#arrow)")
            .attr("stroke", "#f97316") // Orange line
            .attr("opacity", (d) => 0.4 + 0.6 * (d.confidence ?? 0.4));

        const node = g.append("g")
            .selectAll("circle")
            .data(nodes)
            .enter()
            .append("circle")
            .attr("r", (d) => (d.type === "ASSET" ? 10 : d.type === "EVENT" ? 8 : d.type === "NARRATIVE" ? 7 : 6))
            .attr("fill", "currentColor")
            .attr("opacity", (d) => (d.type === "ENTITY" ? 0.45 : 0.85))
            .call(d3.drag()
                .on("start", (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.25).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on("drag", (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on("end", (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                })
            );

        const label = g.append("g")
            .selectAll("text")
            .data(nodes)
            .enter()
            .append("text")
            .text((d) => d.label)
            .attr("font-size", 11)
            .attr("dx", 12)
            .attr("dy", 4)
            .attr("fill", "currentColor")
            .attr("opacity", 0.85);

        // Tooltip
        // Remove old tooltip if any
        d3.select(ref.current.parentElement).select(".graph-tooltip").remove();

        const tooltip = d3.select(ref.current.parentElement)
            .append("div")
            .attr("class", "graph-tooltip")
            .style("position", "absolute")
            .style("pointer-events", "none")
            .style("padding", "8px 10px")
            .style("border-radius", "10px")
            .style("max-width", "420px")
            .style("background", "rgba(0,0,0,0.8)")
            .style("color", "white")
            .style("font-size", "12px")
            .style("z-index", "100")
            .style("opacity", 0);

        function showTooltip(html, x, y) {
            tooltip.html(html)
                .style("left", `${x + 12}px`)
                .style("top", `${y + 12}px`)
                .style("opacity", 1);
        }
        function hideTooltip() {
            tooltip.style("opacity", 0);
        }

        node.on("mousemove", (event, d) => {
            const tags = (d.tags ?? []).join(", ");
            const payload = d.payload ? `<pre style="margin:6px 0 0 0;white-space:pre-wrap;">${JSON.stringify(d.payload, null, 2)}</pre>` : "";
            showTooltip(
                `<div><b>${d.label}</b></div><div>${d.id}</div><div>${d.type}${tags ? ` • ${tags}` : ""}</div>${payload}`,
                event.pageX, event.pageY
            );
        }).on("mouseleave", hideTooltip);

        link.on("mousemove", (event, d) => {
            const ev = (d.evidence ?? []).slice(0, 4).map((x) => `<li>${x}</li>`).join("");
            showTooltip(
                `<div><b>${d.relation}</b> ${d.source.id || d.source} → ${d.target.id || d.target}</div>
         <div>sign: ${d.sign ?? "0"} • strength: ${(d.strength ?? 0.4).toFixed(2)} • conf: ${(d.confidence ?? 0.4).toFixed(2)}</div>
         ${d.condition ? `<div><i>${d.condition}</i></div>` : ""}
         ${ev ? `<ul style="margin:6px 0 0 14px;">${ev}</ul>` : ""}`,
                event.pageX, event.pageY
            );
        }).on("mouseleave", hideTooltip);

        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id((d) => d.id).distance(90).strength(0.4))
            .force("charge", d3.forceManyBody().strength(-260))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(18));

        simulation.on("tick", () => {
            link
                .attr("x1", (d) => d.source.x)
                .attr("y1", (d) => d.source.y)
                .attr("x2", (d) => d.target.x)
                .attr("y2", (d) => d.target.y);

            node
                .attr("cx", (d) => d.x)
                .attr("cy", (d) => d.y);

            label
                .attr("x", (d) => d.x)
                .attr("y", (d) => d.y);
        });

        return () => {
            simulation.stop();
            tooltip.remove();
        };
    }, [filtered]);

    if (!graph) return <div className="p-4 text-gray-500">Loading graph or no data...</div>;

    return (
        <div style={{ position: "relative", width: "100%", height: "780px" }} className="bg-gray-900/50 rounded-lg border border-gray-800 p-4">
            <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 10, flexWrap: "wrap", fontSize: "0.85rem" }} className="text-gray-300">
                <div><span className="text-gray-500">Week</span> <b className="text-white">{graph.week_id}</b> • <span className="text-gray-500">As of</span> <b className="text-white">{graph.asof_et}</b></div>

                <label className="flex items-center gap-2">
                    Min edge score
                    <input
                        type="range"
                        min={0}
                        max={0.6}
                        step={0.02}
                        value={minEdgeScore}
                        onChange={(e) => setMinEdgeScore(parseFloat(e.target.value))}
                        className="w-24 accent-blue-500"
                    />
                    <span style={{ marginLeft: 8 }} className="font-mono text-xs">{minEdgeScore.toFixed(2)}</span>
                </label>

                <label className="flex items-center gap-2">
                    Focus node id
                    <input
                        style={{ width: 180 }}
                        value={focusNodeId}
                        placeholder="e.g., ast:TLT..."
                        onChange={(e) => setFocusNodeId(e.target.value.trim())}
                        className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs placeholder-gray-600 focus:outline-none focus:border-blue-500"
                    />
                </label>

                {focusNodeId && (
                    <button
                        onClick={() => setFocusNodeId("")}
                        className="text-xs text-red-400 hover:text-red-300 underline"
                    >
                        Clear
                    </button>
                )}

                <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    {TYPE_ORDER.map((t) => (
                        <label key={t} style={{ display: "flex", gap: 6, alignItems: "center" }} className="cursor-pointer select-none">
                            <input
                                type="checkbox"
                                checked={typeFilter[t]}
                                onChange={(e) => setTypeFilter({ ...typeFilter, [t]: e.target.checked })}
                                className="accent-blue-500"
                            />
                            <span style={{ fontSize: "0.75rem", opacity: typeFilter[t] ? 1 : 0.5 }}>{t}</span>
                        </label>
                    ))}
                </div>
            </div>

            <svg ref={ref} width="100%" height="720" className="w-full h-full text-white" />
        </div>
    );
}
