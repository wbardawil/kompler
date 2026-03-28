"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { fetchGraph, fetchEntityConnections } from "@/lib/api";
import { Search, X, FileText, ZoomIn, ZoomOut } from "lucide-react";

const TYPE_COLORS: Record<string, string> = {
  document: "#3B82F6",
  person: "#8B5CF6",
  organization: "#10B981",
  regulation: "#F59E0B",
  standard: "#F59E0B",
  certificate: "#EF4444",
  date: "#6B7280",
  location: "#EC4899",
  product: "#06B6D4",
  process: "#14B8A6",
  document_reference: "#3B82F6",
  other: "#9CA3AF",
};

interface GraphNode {
  id: string;
  label: string;
  type: string;
  subtype: string;
  size: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface GraphEdge {
  source: string;
  target: string;
}

export default function GraphPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [graph, setGraph] = useState<any>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [search, setSearch] = useState("");
  const [hovered, setHovered] = useState<GraphNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState<GraphNode | null>(null);
  const [panning, setPanning] = useState(false);
  const [lastMouse, setLastMouse] = useState({ x: 0, y: 0 });
  const animRef = useRef<number>(0);

  // Load graph data
  useEffect(() => {
    fetchGraph().then((data) => {
      setGraph(data);
      initializeLayout(data);
    });
  }, []);

  const initializeLayout = useCallback((data: any) => {
    if (!data?.nodes) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const w = canvas.offsetWidth;
    const h = canvas.offsetHeight;
    const cx = w / 2;
    const cy = h / 2;

    // Deduplicate nodes by label+type
    const seen = new Map<string, GraphNode>();
    const docNodes: GraphNode[] = [];
    const entityNodes: GraphNode[] = [];

    for (const n of data.nodes) {
      const key = `${n.type}:${n.label.toLowerCase()}`;
      if (seen.has(key)) {
        seen.get(key)!.size += n.size;
        continue;
      }
      const node: GraphNode = {
        ...n,
        x: cx + (Math.random() - 0.5) * w * 0.6,
        y: cy + (Math.random() - 0.5) * h * 0.6,
        vx: 0,
        vy: 0,
      };
      seen.set(key, node);
      if (n.type === "document") docNodes.push(node);
      else entityNodes.push(node);
    }

    // Position documents in a circle at center
    docNodes.forEach((n, i) => {
      const angle = (i / docNodes.length) * Math.PI * 2;
      const r = Math.min(w, h) * 0.15;
      n.x = cx + Math.cos(angle) * r;
      n.y = cy + Math.sin(angle) * r;
    });

    // Position entities in outer ring grouped by type
    const types = [...new Set(entityNodes.map((n) => n.subtype))];
    entityNodes.forEach((n) => {
      const typeIdx = types.indexOf(n.subtype);
      const typeEntities = entityNodes.filter((e) => e.subtype === n.subtype);
      const idxInType = typeEntities.indexOf(n);
      const angleBase = (typeIdx / types.length) * Math.PI * 2;
      const angleSpread = (1 / types.length) * Math.PI * 2;
      const angle = angleBase + (idxInType / typeEntities.length) * angleSpread;
      const r = Math.min(w, h) * (0.25 + Math.random() * 0.15);
      n.x = cx + Math.cos(angle) * r;
      n.y = cy + Math.sin(angle) * r;
    });

    const allNodes = [...docNodes, ...entityNodes];

    // Build edge list using deduped node keys
    const edgeList: GraphEdge[] = [];
    for (const e of data.edges || []) {
      const sourceNode = allNodes.find((n) => n.id === e.source);
      const targetNode = allNodes.find((n) => n.id === e.target);
      if (sourceNode && targetNode) {
        edgeList.push({ source: sourceNode.id, target: targetNode.id });
      }
    }

    setNodes(allNodes);
    setEdges(edgeList);
  }, []);

  // Force simulation
  useEffect(() => {
    if (nodes.length === 0) return;

    let iteration = 0;
    const maxIterations = 150;

    const simulate = () => {
      if (iteration > maxIterations) return;
      iteration++;

      const updated = [...nodes];
      const k = 0.01; // spring constant
      const repulsion = 2000;

      // Repulsion between all nodes
      for (let i = 0; i < updated.length; i++) {
        for (let j = i + 1; j < updated.length; j++) {
          const dx = updated[j].x - updated[i].x;
          const dy = updated[j].y - updated[i].y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = repulsion / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          updated[i].vx -= fx;
          updated[i].vy -= fy;
          updated[j].vx += fx;
          updated[j].vy += fy;
        }
      }

      // Attraction along edges
      for (const edge of edges) {
        const source = updated.find((n) => n.id === edge.source);
        const target = updated.find((n) => n.id === edge.target);
        if (!source || !target) continue;
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const force = k * (dist - 100);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        source.vx += fx;
        source.vy += fy;
        target.vx -= fx;
        target.vy -= fy;
      }

      // Apply velocities with damping
      const canvas = canvasRef.current;
      const w = canvas?.offsetWidth || 800;
      const h = canvas?.offsetHeight || 600;
      for (const node of updated) {
        if (dragging && node.id === dragging.id) continue;
        node.vx *= 0.8;
        node.vy *= 0.8;
        node.x += node.vx;
        node.y += node.vy;
        node.x = Math.max(30, Math.min(w - 30, node.x));
        node.y = Math.max(30, Math.min(h - 30, node.y));
      }

      setNodes([...updated]);
      if (iteration < maxIterations) {
        animRef.current = requestAnimationFrame(simulate);
      }
    };

    animRef.current = requestAnimationFrame(simulate);
    return () => cancelAnimationFrame(animRef.current);
  }, [edges.length]); // Only run once when edges are set

  // Draw canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = canvas.offsetHeight * dpr;
    ctx.scale(dpr, dpr);

    const w = canvas.offsetWidth;
    const h = canvas.offsetHeight;

    ctx.clearRect(0, 0, w, h);
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Draw edges
    ctx.strokeStyle = "rgba(200, 200, 210, 0.3)";
    ctx.lineWidth = 0.5;
    for (const edge of edges) {
      const source = nodes.find((n) => n.id === edge.source);
      const target = nodes.find((n) => n.id === edge.target);
      if (!source || !target) continue;

      const isHighlighted =
        selected && (source.id === selected.id || target.id === selected.id);

      ctx.strokeStyle = isHighlighted
        ? "rgba(79, 109, 245, 0.6)"
        : "rgba(200, 200, 210, 0.2)";
      ctx.lineWidth = isHighlighted ? 1.5 : 0.5;
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.stroke();
    }

    // Draw nodes
    const searchLower = search.toLowerCase();
    for (const node of nodes) {
      const color = TYPE_COLORS[node.subtype] || TYPE_COLORS[node.type] || "#9CA3AF";
      const isSelected = selected?.id === node.id;
      const isHovered = hovered?.id === node.id;
      const isSearchMatch = search && node.label.toLowerCase().includes(searchLower);
      const isDimmed = search && !isSearchMatch;

      const radius = node.type === "document" ? 8 : 4 + Math.min(node.size, 6);

      ctx.globalAlpha = isDimmed ? 0.15 : 1;

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      if (isSelected || isHovered) {
        ctx.strokeStyle = "#1a1a1a";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Label (only for documents, selected, hovered, or search matches)
      if (
        node.type === "document" ||
        isSelected ||
        isHovered ||
        isSearchMatch ||
        node.size >= 3
      ) {
        ctx.fillStyle = isDimmed ? "rgba(0,0,0,0.1)" : "#1a1a1a";
        ctx.font = `${isSelected || isHovered ? "bold " : ""}${
          node.type === "document" ? 10 : 9
        }px system-ui`;
        ctx.textAlign = "center";
        const label =
          node.label.length > 25 ? node.label.slice(0, 22) + "..." : node.label;
        ctx.fillText(label, node.x, node.y + radius + 12);
      }

      ctx.globalAlpha = 1;
    }

    ctx.restore();
  }, [nodes, edges, selected, hovered, search, zoom, pan]);

  // Mouse handlers
  const getNodeAtPos = (mx: number, my: number): GraphNode | null => {
    const x = (mx - pan.x) / zoom;
    const y = (my - pan.y) / zoom;
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      const r = n.type === "document" ? 10 : 6 + Math.min(n.size, 6);
      const dx = n.x - x;
      const dy = n.y - y;
      if (dx * dx + dy * dy < r * r * 4) return n;
    }
    return null;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    if (dragging) {
      const x = (mx - pan.x) / zoom;
      const y = (my - pan.y) / zoom;
      dragging.x = x;
      dragging.y = y;
      setNodes([...nodes]);
    } else if (panning) {
      setPan({
        x: pan.x + (mx - lastMouse.x),
        y: pan.y + (my - lastMouse.y),
      });
      setLastMouse({ x: mx, y: my });
    } else {
      const node = getNodeAtPos(mx, my);
      setHovered(node);
      if (canvasRef.current) {
        canvasRef.current.style.cursor = node ? "pointer" : "grab";
      }
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const node = getNodeAtPos(mx, my);

    if (node) {
      setDragging(node);
    } else {
      setPanning(true);
      setLastMouse({ x: mx, y: my });
    }
  };

  const handleMouseUp = async () => {
    if (dragging && !panning) {
      // If we just clicked (not dragged far), select it
      setSelected(dragging);
      if (dragging.type === "entity") {
        const connections = await fetchEntityConnections(dragging.label);
        setDetail(connections);
      } else {
        setDetail(null);
      }
    }
    setDragging(null);
    setPanning(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(Math.max(0.3, Math.min(3, zoom * delta)));
  };

  if (!graph) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-gray-500">Loading knowledge graph...</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Top Bar */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Knowledge Graph</h2>
          <p className="text-xs text-gray-500">
            {graph.stats?.entity_count} entities, {graph.stats?.document_count} documents,{" "}
            {graph.stats?.cross_document_entities} cross-doc links
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Highlight entity..."
              className="pl-8 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm w-56 focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button onClick={() => setZoom(zoom * 1.2)} className="p-1.5 border rounded hover:bg-gray-50">
            <ZoomIn size={16} />
          </button>
          <button onClick={() => setZoom(zoom * 0.8)} className="p-1.5 border rounded hover:bg-gray-50">
            <ZoomOut size={16} />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-3">
        {Object.entries(graph.stats?.entity_types || {}).map(([type, count]) => (
          <button
            key={type}
            onClick={() => setSearch(search === type ? "" : type)}
            className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border transition-colors ${
              search === type ? "bg-gray-900 text-white border-gray-900" : "bg-white border-gray-200 hover:bg-gray-50"
            }`}
          >
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TYPE_COLORS[type] || "#9CA3AF" }} />
            {type} ({count as number})
          </button>
        ))}
        <span className="flex items-center gap-1.5 text-xs text-gray-400">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
          documents
        </span>
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* Canvas */}
        <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden relative">
          <canvas
            ref={canvasRef}
            className="w-full h-full"
            onMouseMove={handleMouseMove}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => { setDragging(null); setPanning(false); setHovered(null); }}
            onWheel={handleWheel}
          />
        </div>

        {/* Detail Panel */}
        {selected && detail && (
          <div className="w-80 bg-white rounded-xl border border-gray-200 p-4 overflow-y-auto flex-shrink-0">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: TYPE_COLORS[selected.subtype] || "#9CA3AF" }} />
                <h3 className="font-bold text-gray-900 text-sm">{selected.label}</h3>
              </div>
              <button onClick={() => { setSelected(null); setDetail(null); }} className="p-1 hover:bg-gray-100 rounded">
                <X size={14} />
              </button>
            </div>
            <p className="text-xs text-gray-500 capitalize mb-3">{selected.subtype}</p>

            {/* Documents */}
            <h4 className="text-xs font-semibold text-gray-600 mb-2">
              In {detail.mention_count} document{detail.mention_count !== 1 ? "s" : ""}
            </h4>
            <div className="space-y-2 mb-4">
              {detail.documents?.map((doc: any, i: number) => (
                <div key={i} className="bg-blue-50 rounded-lg p-2.5">
                  <div className="flex items-center gap-2">
                    <FileText size={12} className="text-blue-500" />
                    <p className="text-xs font-medium text-blue-900 truncate">{doc.filename}</p>
                  </div>
                  {doc.doc_type && (
                    <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded mt-1 inline-block">{doc.doc_type}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Related */}
            {detail.related_entities?.length > 0 && (
              <>
                <h4 className="text-xs font-semibold text-gray-600 mb-2">Related entities</h4>
                <div className="flex flex-wrap gap-1.5">
                  {detail.related_entities.slice(0, 15).map((rel: any, i: number) => (
                    <button
                      key={i}
                      onClick={async () => {
                        const node = nodes.find((n) => n.label.toLowerCase() === rel.value.toLowerCase());
                        if (node) {
                          setSelected(node);
                          const conn = await fetchEntityConnections(node.label);
                          setDetail(conn);
                        }
                      }}
                      className="text-[11px] bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-full px-2 py-1 flex items-center gap-1"
                    >
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: TYPE_COLORS[rel.type] || "#9CA3AF" }} />
                      {rel.value}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
