# benchmark/report.py
"""
Report Generator - Creates HTML reports from benchmark results.
Emphasizes ACCURACY as the primary metric.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Benchmark Report</title>
    <style>
        :root {
            --bg: #0a0a0f;
            --surface: #12121a;
            --card: #1a1a25;
            --border: #2a2a3a;
            --text: #e0e0e8;
            --text-dim: #8888a0;
            --accent: #6366f1;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }
        
        .container { max-width: 1600px; margin: 0 auto; }
        
        header {
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: linear-gradient(135deg, var(--surface), var(--card));
            border-radius: 16px;
            border: 1px solid var(--border);
        }
        
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .subtitle { color: var(--text-dim); font-size: 1.1rem; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        
        .stat-card {
            background: var(--card);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            text-align: center;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
        }
        
        .stat-label {
            color: var(--text-dim);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }
        
        .section {
            background: var(--surface);
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .section h2 {
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        
        th, td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        
        th {
            background: var(--card);
            color: var(--text-dim);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            cursor: pointer;
        }
        
        th:hover { color: var(--accent); }
        
        tr:hover { background: rgba(99, 102, 241, 0.05); }
        
        .rank { 
            font-weight: 700; 
            color: var(--accent);
            width: 50px;
        }
        
        .rank.gold { color: #fbbf24; }
        .rank.silver { color: #9ca3af; }
        .rank.bronze { color: #cd7f32; }
        
        .model-name {
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
        }
        
        .score-bar {
            background: var(--card);
            border-radius: 4px;
            height: 24px;
            overflow: hidden;
            position: relative;
        }
        
        .score-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .score-bar-text {
            position: absolute;
            left: 8px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .accuracy { background: linear-gradient(90deg, #22c55e, #86efac); }
        .time { background: linear-gradient(90deg, #6366f1, #a5b4fc); }
        
        .field-accuracy {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .field-badge {
            background: var(--card);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-family: monospace;
        }
        
        .error-rate {
            color: var(--danger);
            font-weight: 600;
        }
        
        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-dim);
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            body { padding: 1rem; }
            h1 { font-size: 1.75rem; }
            th, td { padding: 0.5rem; }
            .model-name { font-size: 0.75rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Model Benchmark Report</h1>
            <p class="subtitle">{{SUBTITLE}}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{TOTAL_MODELS}}</div>
                <div class="stat-label">Models Tested</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{TOTAL_CASES}}</div>
                <div class="stat-label">Test Cases</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{RUNS_PER_CASE}}</div>
                <div class="stat-label">Runs per Case</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{TOTAL_TIME}}</div>
                <div class="stat-label">Total Runtime</div>
            </div>
        </div>
        
        <section class="section">
            <h2>🏆 Model Rankings (Accuracy is King)</h2>
            <table id="rankings">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Rank</th>
                        <th onclick="sortTable(1)">Model</th>
                        <th onclick="sortTable(2)">Composite Score</th>
                        <th onclick="sortTable(3)">F1 Score</th>
                        <th onclick="sortTable(4)">Accuracy</th>
                        <th onclick="sortTable(5)">Parse Rate</th>
                        <th onclick="sortTable(6)">Consistency</th>
                        <th onclick="sortTable(7)">Avg Time</th>
                        <th onclick="sortTable(8)">Total Time</th>
                    </tr>
                </thead>
                <tbody>
                    {{RANKING_ROWS}}
                </tbody>
            </table>
        </section>
        
        <section class="section">
            <h2>📊 Field-Level Accuracy</h2>
            <table>
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Pick (40%)</th>
                        <th>League (20%)</th>
                        <th>Type (15%)</th>
                        <th>Capper (10%)</th>
                        <th>Odds (10%)</th>
                        <th>Units (5%)</th>
                    </tr>
                </thead>
                <tbody>
                    {{FIELD_ACCURACY_ROWS}}
                </tbody>
            </table>
        </section>
        
        <footer>
            <p>Generated on {{TIMESTAMP}} | Benchmark Suite v1.0</p>
            <p>Accuracy Weight: 85% | Time Weight: 15%</p>
        </footer>
    </div>
    
    <script>
        function sortTable(n) {
            const table = document.getElementById("rankings");
            const rows = Array.from(table.tBodies[0].rows);
            const dir = table.dataset.sortDir === 'asc' ? -1 : 1;
            table.dataset.sortDir = dir === 1 ? 'asc' : 'desc';
            
            rows.sort((a, b) => {
                let aVal = a.cells[n].dataset.value || a.cells[n].textContent;
                let bVal = b.cells[n].dataset.value || b.cells[n].textContent;
                if (!isNaN(aVal)) aVal = parseFloat(aVal);
                if (!isNaN(bVal)) bVal = parseFloat(bVal);
                return aVal > bVal ? dir : aVal < bVal ? -dir : 0;
            });
            
            rows.forEach(row => table.tBodies[0].appendChild(row));
        }
    </script>
</body>
</html>
"""


def generate_score_bar(value: float, max_val: float, css_class: str) -> str:
    """Generate HTML for a score bar."""
    pct = min(100, (value / max_val) * 100) if max_val > 0 else 0
    return f'''
        <div class="score-bar">
            <div class="score-bar-fill {css_class}" style="width: {pct:.1f}%"></div>
            <span class="score-bar-text">{value:.2f}</span>
        </div>
    '''


def format_time(ms: float) -> str:
    """Format milliseconds to readable string."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms/1000:.1f}s"


def generate_report(results_file: str = "benchmark_results/raw_results.json", output_file: str = "benchmark_results/report.html"):
    """Generate HTML report from results JSON."""
    
    results_path = Path(results_file)
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found: {results_file}")
    
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    if not results:
        raise ValueError("No results to generate report from")
    
    # Sort by composite score (descending)
    sorted_models = sorted(results.items(), key=lambda x: x[1].get("composite_score", 0), reverse=True)
    
    # Calculate totals
    total_models = len(results)
    first_result = list(results.values())[0] if results else {}
    num_cases = first_result.get("num_cases", 0)
    
    # Estimate runs per case (cases are run multiple times)
    case_results = first_result.get("case_results", [])
    unique_cases = len(set(cr.get("case_id") for cr in case_results))
    runs_per_case = len(case_results) // unique_cases if unique_cases > 0 else 1
    
    total_time_ms = sum(r.get("total_time_ms", 0) for r in results.values())
    total_time_str = f"{total_time_ms/1000/60:.1f} min" if total_time_ms > 60000 else f"{total_time_ms/1000:.1f}s"
    
    # Generate ranking rows
    ranking_rows = []
    for rank, (model, data) in enumerate(sorted_models, 1):
        rank_class = ""
        if rank == 1: rank_class = "gold"
        elif rank == 2: rank_class = "silver"
        elif rank == 3: rank_class = "bronze"
        
        composite = data.get("composite_score", 0)
        f1 = data.get("avg_f1", 0)
        accuracy = data.get("avg_accuracy", 0)
        parse_rate = data.get("parse_success_rate", 0)
        consistency = data.get("consistency_score", 0)
        avg_time = data.get("avg_response_time_ms", 0)
        total_time = data.get("total_time_ms", 0)
        
        ranking_rows.append(f'''
            <tr>
                <td class="rank {rank_class}">{rank}</td>
                <td class="model-name">{model}</td>
                <td data-value="{composite:.4f}">{composite:.2f}</td>
                <td data-value="{f1:.4f}">{generate_score_bar(f1, 1.0, 'accuracy')}</td>
                <td data-value="{accuracy:.4f}">{accuracy:.1%}</td>
                <td data-value="{parse_rate:.4f}">{parse_rate:.1%}</td>
                <td data-value="{consistency:.4f}">{consistency:.1%}</td>
                <td data-value="{avg_time:.0f}">{format_time(avg_time)}</td>
                <td data-value="{total_time:.0f}">{format_time(total_time)}</td>
            </tr>
        ''')
    
    # Generate field accuracy rows
    field_rows = []
    for model, data in sorted_models[:20]:  # Top 20 only
        fa = data.get("field_accuracy", {})
        field_rows.append(f'''
            <tr>
                <td class="model-name">{model}</td>
                <td>{fa.get('p', 0):.1%}</td>
                <td>{fa.get('lg', 0):.1%}</td>
                <td>{fa.get('ty', 0):.1%}</td>
                <td>{fa.get('cn', 0):.1%}</td>
                <td>{fa.get('od', 0):.1%}</td>
                <td>{fa.get('u', 0):.1%}</td>
            </tr>
        ''')
    
    # Build final HTML
    html = HTML_TEMPLATE.replace("{{SUBTITLE}}", f"Tested {total_models} models across {unique_cases} test cases")
    html = html.replace("{{TOTAL_MODELS}}", str(total_models))
    html = html.replace("{{TOTAL_CASES}}", str(unique_cases))
    html = html.replace("{{RUNS_PER_CASE}}", str(runs_per_case))
    html = html.replace("{{TOTAL_TIME}}", total_time_str)
    html = html.replace("{{RANKING_ROWS}}", "\n".join(ranking_rows))
    html = html.replace("{{FIELD_ACCURACY_ROWS}}", "\n".join(field_rows))
    html = html.replace("{{TIMESTAMP}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Write output
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"📄 Report generated: {output_path.absolute()}")
    return output_path


if __name__ == "__main__":
    generate_report()
