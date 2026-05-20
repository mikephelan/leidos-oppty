#!/usr/bin/env python3
"""
Visualize CFR-Order mappings from the mappings.json file.

This script creates interactive HTML visualizations showing:
- Network graph of CFR sections and FAA Orders
- Heatmap of mapping relationships
- Statistics dashboard
- Top referenced sections and orders
"""
import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_mappings(json_file: str) -> List[Dict[str, Any]]:
    """Load mappings from JSON file."""
    logger.info(f"Loading mappings from {json_file}")
    with open(json_file, 'r') as f:
        mappings = json.load(f)
    logger.info(f"Loaded {len(mappings)} mappings")
    return mappings


def generate_statistics(mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate statistics from mappings."""
    logger.info("Generating statistics...")
    
    cfr_sections = set()
    orders = set()
    relationship_types = Counter()
    confidence_scores = []
    extraction_methods = Counter()
    
    cfr_to_orders = defaultdict(set)
    order_to_cfrs = defaultdict(set)
    
    for mapping in mappings:
        cfr_section = mapping['cfr_section']
        order_number = mapping['order_number']
        
        cfr_sections.add(cfr_section)
        orders.add(order_number)
        relationship_types[mapping['relationship_type']] += 1
        confidence_scores.append(mapping['confidence_score'])
        extraction_methods[mapping['extraction_method']] += 1
        
        cfr_to_orders[cfr_section].add(order_number)
        order_to_cfrs[order_number].add(cfr_section)
    
    # Top CFR sections by number of orders
    top_cfr_sections = sorted(
        [(cfr, len(orders)) for cfr, orders in cfr_to_orders.items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]
    
    # Top orders by number of CFR sections
    top_orders = sorted(
        [(order, len(cfrs)) for order, cfrs in order_to_cfrs.items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]
    
    stats = {
        'total_mappings': len(mappings),
        'unique_cfr_sections': len(cfr_sections),
        'unique_orders': len(orders),
        'relationship_types': dict(relationship_types),
        'avg_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
        'extraction_methods': dict(extraction_methods),
        'top_cfr_sections': top_cfr_sections,
        'top_orders': top_orders,
        'cfr_to_orders': {k: list(v) for k, v in cfr_to_orders.items()},
        'order_to_cfrs': {k: list(v) for k, v in order_to_cfrs.items()}
    }
    
    return stats


def generate_network_graph_html(mappings: List[Dict[str, Any]], stats: Dict[str, Any], output_file: str):
    """Generate interactive network graph visualization using vis.js."""
    logger.info(f"Generating network graph: {output_file}")
    
    # Prepare nodes and edges for top connections only (to keep it manageable)
    nodes = []
    edges = []
    node_ids = set()
    
    # Add top CFR sections as nodes
    for cfr_section, count in stats['top_cfr_sections'][:15]:
        node_id = f"cfr_{cfr_section}"
        if node_id not in node_ids:
            nodes.append({
                'id': node_id,
                'label': f"CFR §{cfr_section}",
                'group': 'cfr',
                'title': f"CFR §{cfr_section}<br>Referenced by {count} orders",
                'value': count
            })
            node_ids.add(node_id)
    
    # Add top orders as nodes
    for order_number, count in stats['top_orders'][:15]:
        node_id = f"order_{order_number}"
        if node_id not in node_ids:
            nodes.append({
                'id': node_id,
                'label': order_number,
                'group': 'order',
                'title': f"Order {order_number}<br>References {count} CFR sections",
                'value': count
            })
            node_ids.add(node_id)
    
    # Add edges for mappings between top nodes
    edge_set = set()
    for mapping in mappings:
        cfr_id = f"cfr_{mapping['cfr_section']}"
        order_id = f"order_{mapping['order_number']}"
        
        if cfr_id in node_ids and order_id in node_ids:
            edge_key = (cfr_id, order_id)
            if edge_key not in edge_set:
                edges.append({
                    'from': cfr_id,
                    'to': order_id,
                    'title': f"Confidence: {mapping['confidence_score']:.2f}",
                    'value': mapping['confidence_score']
                })
                edge_set.add(edge_key)
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>CFR-Order Mapping Network</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        #mynetwork {{
            width: 100%;
            height: 700px;
            border: 1px solid #ddd;
            background-color: white;
            margin: 20px 0;
        }}
        .info {{
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 20px 0;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }}
        .cfr-color {{ background-color: #97C2FC; }}
        .order-color {{ background-color: #FB7E81; }}
    </style>
</head>
<body>
    <h1>CFR-Order Mapping Network Visualization</h1>
    
    <div class="info">
        <h3>Network Overview</h3>
        <p>This network shows the relationships between CFR sections (blue) and FAA Orders (red).</p>
        <p>Node size represents the number of connections. Hover over nodes and edges for details.</p>
        <p><strong>Showing top 15 CFR sections and top 15 Orders by connection count.</strong></p>
    </div>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-color cfr-color"></div>
            <span>CFR Sections</span>
        </div>
        <div class="legend-item">
            <div class="legend-color order-color"></div>
            <span>FAA Orders</span>
        </div>
    </div>
    
    <div id="mynetwork"></div>
    
    <div class="info">
        <h3>Statistics</h3>
        <ul>
            <li>Total Mappings: {stats['total_mappings']}</li>
            <li>Unique CFR Sections: {stats['unique_cfr_sections']}</li>
            <li>Unique FAA Orders: {stats['unique_orders']}</li>
            <li>Average Confidence Score: {stats['avg_confidence']:.3f}</li>
        </ul>
    </div>
    
    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(nodes)});
        var edges = new vis.DataSet({json.dumps(edges)});
        
        var container = document.getElementById('mynetwork');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        
        var options = {{
            nodes: {{
                shape: 'dot',
                scaling: {{
                    min: 10,
                    max: 30
                }},
                font: {{
                    size: 12,
                    face: 'Arial'
                }}
            }},
            edges: {{
                width: 0.5,
                color: {{
                    inherit: 'from',
                    opacity: 0.4
                }},
                smooth: {{
                    type: 'continuous'
                }}
            }},
            groups: {{
                cfr: {{
                    color: {{
                        background: '#97C2FC',
                        border: '#2B7CE9'
                    }}
                }},
                order: {{
                    color: {{
                        background: '#FB7E81',
                        border: '#E92B2B'
                    }}
                }}
            }},
            physics: {{
                stabilization: false,
                barnesHut: {{
                    gravitationalConstant: -8000,
                    springConstant: 0.001,
                    springLength: 200
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 100
            }}
        }};
        
        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>"""
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Network graph saved to {output_file}")


def generate_dashboard_html(mappings: List[Dict[str, Any]], stats: Dict[str, Any], output_file: str):
    """Generate statistics dashboard with charts."""
    logger.info(f"Generating dashboard: {output_file}")
    
    # Prepare data for charts
    top_cfr_labels = [f"§{cfr}" for cfr, _ in stats['top_cfr_sections'][:10]]
    top_cfr_values = [count for _, count in stats['top_cfr_sections'][:10]]
    
    top_order_labels = [order for order, _ in stats['top_orders'][:10]]
    top_order_values = [count for _, count in stats['top_orders'][:10]]
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>CFR-Order Mapping Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1, h2 {{
            color: #333;
            text-align: center;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2B7CE9;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .chart-wrapper {{
            position: relative;
            height: 400px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #2B7CE9;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>CFR-Order Mapping Dashboard</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Mappings</div>
                <div class="stat-value">{stats['total_mappings']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Unique CFR Sections</div>
                <div class="stat-value">{stats['unique_cfr_sections']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Unique FAA Orders</div>
                <div class="stat-value">{stats['unique_orders']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Confidence</div>
                <div class="stat-value">{stats['avg_confidence']:.2f}</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>Top 10 Most Referenced CFR Sections</h2>
            <div class="chart-wrapper">
                <canvas id="cfrChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>Top 10 Orders by CFR References</h2>
            <div class="chart-wrapper">
                <canvas id="orderChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>Relationship Types Distribution</h2>
            <div class="chart-wrapper">
                <canvas id="relationshipChart"></canvas>
            </div>
        </div>
        
        <h2>Top CFR Sections Details</h2>
        <table>
            <thead>
                <tr>
                    <th>CFR Section</th>
                    <th>Number of Orders</th>
                    <th>Orders</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f'<tr><td>§{cfr}</td><td>{count}</td><td>{", ".join(stats["cfr_to_orders"][cfr][:5])}{" ..." if len(stats["cfr_to_orders"][cfr]) > 5 else ""}</td></tr>' for cfr, count in stats['top_cfr_sections'][:15]])}
            </tbody>
        </table>
        
        <h2>Top Orders Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Order Number</th>
                    <th>Number of CFR Sections</th>
                    <th>CFR Sections</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f'<tr><td>{order}</td><td>{count}</td><td>{", ".join(["§" + cfr for cfr in stats["order_to_cfrs"][order][:5]])}{" ..." if len(stats["order_to_cfrs"][order]) > 5 else ""}</td></tr>' for order, count in stats['top_orders'][:15]])}
            </tbody>
        </table>
    </div>
    
    <script>
        // Top CFR Sections Chart
        const cfrCtx = document.getElementById('cfrChart').getContext('2d');
        new Chart(cfrCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(top_cfr_labels)},
                datasets: [{{
                    label: 'Number of Orders',
                    data: {json.dumps(top_cfr_values)},
                    backgroundColor: 'rgba(43, 124, 233, 0.7)',
                    borderColor: 'rgba(43, 124, 233, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }}
            }}
        }});
        
        // Top Orders Chart
        const orderCtx = document.getElementById('orderChart').getContext('2d');
        new Chart(orderCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(top_order_labels)},
                datasets: [{{
                    label: 'Number of CFR Sections',
                    data: {json.dumps(top_order_values)},
                    backgroundColor: 'rgba(251, 126, 129, 0.7)',
                    borderColor: 'rgba(251, 126, 129, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }}
            }}
        }});
        
        // Relationship Types Chart
        const relationshipCtx = document.getElementById('relationshipChart').getContext('2d');
        new Chart(relationshipCtx, {{
            type: 'pie',
            data: {{
                labels: {json.dumps(list(stats['relationship_types'].keys()))},
                datasets: [{{
                    data: {json.dumps(list(stats['relationship_types'].values()))},
                    backgroundColor: [
                        'rgba(43, 124, 233, 0.7)',
                        'rgba(251, 126, 129, 0.7)',
                        'rgba(151, 194, 252, 0.7)',
                        'rgba(255, 206, 86, 0.7)'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
    </script>
</body>
</html>"""
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Dashboard saved to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Visualize CFR-Order mappings from JSON file'
    )
    
    parser.add_argument(
        'json_file',
        type=str,
        help='Path to mappings JSON file'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/visualizations',
        help='Output directory for visualizations (default: data/visualizations)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load mappings
        mappings = load_mappings(args.json_file)
        
        # Generate statistics
        stats = generate_statistics(mappings)
        
        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate visualizations
        generate_network_graph_html(
            mappings,
            stats,
            str(output_dir / 'network_graph.html')
        )
        
        generate_dashboard_html(
            mappings,
            stats,
            str(output_dir / 'dashboard.html')
        )
        
        logger.info("\n" + "="*60)
        logger.info("Visualization complete!")
        logger.info("="*60)
        logger.info(f"Network Graph: {output_dir / 'network_graph.html'}")
        logger.info(f"Dashboard: {output_dir / 'dashboard.html'}")
        logger.info("\nOpen these HTML files in your browser to view the visualizations.")
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        return 1
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

# Made with Bob