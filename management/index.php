<?php
/**
 * Delta Trade Management & Alerting Console.
 * Laravel / PHP High-Speed Risk Management & Surveillance Hub.
 */

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require_once __DIR__ . '/risk_manager.php';
require_once __DIR__ . '/alerting.php';

$riskManager = new RiskManager();
$alertDispatcher = new AlertDispatcher();

$requestUri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);

// API Routes
if (strpos($requestUri, '/api/risk') !== false) {
    header('Content-Type: application/json');

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $input = json_decode(file_get_contents('php://input'), true);
        if (isset($input['kill_switch'])) {
            $riskManager->setKillSwitch((bool)$input['kill_switch']);
        }
    }

    echo json_encode($riskManager->getRiskMetrics());
    exit;
}

if (strpos($requestUri, '/api/alerts') !== false) {
    header('Content-Type: application/json');
    echo json_encode([
        'alerts' => $alertDispatcher->getRecentAlerts(30)
    ]);
    exit;
}

// Interactive Web Console
$metrics = $riskManager->getRiskMetrics();
$alerts = $alertDispatcher->getRecentAlerts(10);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Delta Trade | Risk & Alerting Console</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #07090e;
            --card-bg: rgba(15, 21, 32, 0.85);
            --border: rgba(255, 255, 255, 0.08);
            --cyan: #00f0ff;
            --green: #00ff9d;
            --red: #ff3366;
            --amber: #ffb800;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-dark);
            color: #f1f5f9;
            font-family: 'Inter', sans-serif;
            padding: 24px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }
        .title {
            font-size: 20px;
            font-weight: 800;
            background: linear-gradient(to right, var(--cyan), var(--green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-family: 'JetBrains Mono', monospace;
        }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            font-family: 'JetBrains Mono', monospace;
        }
        .card-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px; }
        .card-val { font-size: 20px; font-weight: 700; color: #f8fafc; }
        .btn-halt {
            background: linear-gradient(135deg, rgba(255, 51, 102, 0.2), rgba(255, 51, 102, 0.05));
            border: 1px solid var(--red);
            color: var(--red);
            padding: 8px 16px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            cursor: pointer;
        }
        .btn-resume {
            background: linear-gradient(135deg, rgba(0, 255, 157, 0.2), rgba(0, 255, 157, 0.05));
            border: 1px solid var(--green);
            color: var(--green);
            padding: 8px 16px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            cursor: pointer;
        }
        table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 12px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
        th { color: #64748b; font-size: 10px; text-transform: uppercase; }
        .badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; }
        .badge-green { background: rgba(0, 255, 157, 0.15); color: var(--green); border: 1px solid rgba(0, 255, 157, 0.3); }
        .badge-red { background: rgba(255, 51, 102, 0.15); color: var(--red); border: 1px solid rgba(255, 51, 102, 0.3); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <div class="title">DELTA TRADE | RISK & ALERTING HUB</div>
                <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Management Service & Real-Time Dispatcher</div>
            </div>
            <div>
                <form method="POST" action="/api/risk">
                    <input type="hidden" name="kill_switch" value="<?= $metrics['kill_switch'] ? '0' : '1' ?>">
                    <button type="submit" class="<?= $metrics['kill_switch'] ? 'btn-resume' : 'btn-halt' ?>">
                        <?= $metrics['kill_switch'] ? 'RESUME EXECUTION ENGINE' : 'EMERGENCY KILL SWITCH' ?>
                    </button>
                </form>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-label">System State</div>
                <div class="card-val" style="color: <?= $metrics['kill_switch'] ? 'var(--red)' : 'var(--green)' ?>;">
                    <?= $metrics['status'] ?>
                </div>
            </div>
            <div class="card">
                <div class="card-label">Max Order Capital</div>
                <div class="card-val">$<?= number_format($metrics['max_capital_per_trade']) ?></div>
            </div>
            <div class="card">
                <div class="card-label">Net Executed PnL</div>
                <div class="card-val" style="color: var(--green);">$<?= number_format($metrics['net_pnl_usd'] ?? 0, 2) ?></div>
            </div>
            <div class="card">
                <div class="card-label">Total Fee Drag</div>
                <div class="card-val" style="color: var(--amber);">$<?= number_format($metrics['total_fee_drag_usd'] ?? 0, 2) ?></div>
            </div>
        </div>

        <div class="card">
            <div class="card-label" style="margin-bottom: 12px;">Active Sub-Second Surveillance Alerts</div>
            <?php if (empty($alerts)): ?>
                <div style="color: #64748b; font-size: 12px; padding: 16px 0;">No critical risk alerts recorded. Surveillance operating within tolerance.</div>
            <?php else: ?>
                <table>
                    <thead>
                        <tr>
                            <th>Alert ID</th>
                            <th>Severity</th>
                            <th>Route</th>
                            <th>Net Spread</th>
                            <th>Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($alerts as $a): ?>
                            <tr>
                                <td style="color: var(--cyan);"><?= htmlspecialchars($a['alert_id'] ?? '') ?></td>
                                <td>
                                    <span class="badge <?= ($a['severity'] ?? '') === 'CRITICAL' ? 'badge-red' : 'badge-green' ?>">
                                        <?= htmlspecialchars($a['severity'] ?? 'INFO') ?>
                                    </span>
                                </td>
                                <td><?= htmlspecialchars(implode(' → ', $a['path'] ?? [])) ?></td>
                                <td style="color: var(--green); font-weight: bold;">+<?= number_format($a['net_spread_bps'] ?? 0, 2) ?> bps</td>
                                <td style="color: #64748b;"><?= htmlspecialchars($a['detected_at'] ?? '') ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
