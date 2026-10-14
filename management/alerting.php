<?php
/**
 * Delta Trade Alerting & Notification Dispatcher.
 * Dispatches sub-second opportunity spreads, active arbitrage routes,
 * and high-slippage alerts to webhooks and connected monitoring consoles.
 */

class AlertDispatcher {
    private $alertsLogFile;
    private $minAlertSpreadBps = 10.0; // Alert if spread >= 10 bps

    public function __construct(string $logFile = __DIR__ . '/alerts.json') {
        $this->alertsLogFile = $logFile;
    }

    public function processOpportunity(array $route): ?array {
        $netSpread = (float)($route['net_spread_bps'] ?? 0);
        
        if ($netSpread >= $this->minAlertSpreadBps) {
            $alert = [
                'alert_id' => 'ALT-' . strtoupper(substr(md5(uniqid()), 0, 8)),
                'type' => 'HIGH_SPREAD_ARBITRAGE',
                'severity' => $netSpread >= 20.0 ? 'CRITICAL' : 'INFO',
                'net_spread_bps' => $netSpread,
                'path' => $route['path'] ?? [],
                'exchanges' => $route['exchanges'] ?? [],
                'expected_profit_usd' => $route['expected_profit_usd'] ?? 0,
                'detected_at' => date('Y-m-d H:i:s.u'),
                'message' => "High-spread {$route['route_type']} opportunity: +" . round($netSpread, 2) . " bps via " . implode(' -> ', $route['path'] ?? [])
            ];

            $this->recordAlert($alert);
            return $alert;
        }

        return null;
    }

    public function recordAlert(array $alert): void {
        $alerts = $this->getRecentAlerts(49);
        array_unshift($alerts, $alert);
        file_put_contents($this->alertsLogFile, json_encode($alerts, JSON_PRETTY_PRINT));
    }

    public function getRecentAlerts(int $limit = 20): array {
        if (!file_exists($this->alertsLogFile)) {
            return [];
        }
        $data = json_decode(file_get_contents($this->alertsLogFile), true);
        return is_array($data) ? array_slice($data, 0, $limit) : [];
    }
}
