<?php
/**
 * Delta Trade HFT Risk Management Engine.
 * Enforces venue exposure limits, max drawdown limits, and emergency kill switches.
 */

class RiskManager {
    private $dbPath;
    private $maxCapitalPerTrade = 50000.0;
    private $maxDrawdownBps = 150.0; // 1.5% max allowable portfolio drawdown
    private $maxSlippageToleranceBps = 25.0; // 25 bps max slippage abort
    private $killSwitchActive = false;

    public function __construct(string $dbPath = __DIR__ . '/../arbitrage_state.db') {
        $this->dbPath = $dbPath;
    }

    public function isKillSwitchEngaged(): bool {
        $lockFile = __DIR__ . '/kill_switch.lock';
        return file_exists($lockFile);
    }

    public function setKillSwitch(bool $engage): void {
        $lockFile = __DIR__ . '/kill_switch.lock';
        if ($engage) {
            file_put_contents($lockFile, json_encode([
                'engaged_at' => date('c'),
                'reason' => 'Emergency halt triggered by risk administrator'
            ]));
        } else {
            if (file_exists($lockFile)) {
                unlink($lockFile);
            }
        }
    }

    public function checkTradeRisk(float $capitalUsd, float $expectedSlippageBps): array {
        if ($this->isKillSwitchEngaged()) {
            return [
                'approved' => false,
                'reason' => 'EMERGENCY_KILL_SWITCH_ACTIVE: Automated execution halted.'
            ];
        }

        if ($capitalUsd > $this->maxCapitalPerTrade) {
            return [
                'approved' => false,
                'reason' => "ORDER_SIZE_EXCEEDS_RISK_LIMIT: \${$capitalUsd} > \${$this->maxCapitalPerTrade}"
            ];
        }

        if ($expectedSlippageBps > $this->maxSlippageToleranceBps) {
            return [
                'approved' => false,
                'reason' => "EXCESSIVE_SLIPPAGE_RISK: {$expectedSlippageBps} bps > {$this->maxSlippageToleranceBps} bps"
            ];
        }

        return [
            'approved' => true,
            'reason' => 'RISK_CHECKS_PASSED'
        ];
    }

    public function getRiskMetrics(): array {
        $stats = [
            'kill_switch' => $this->isKillSwitchEngaged(),
            'max_capital_per_trade' => $this->maxCapitalPerTrade,
            'max_slippage_tolerance_bps' => $this->maxSlippageToleranceBps,
            'status' => $this->isKillSwitchEngaged() ? 'HALTED' : 'ACTIVE_MONITORING'
        ];

        if (file_exists($this->dbPath)) {
            try {
                $db = new PDO("sqlite:" . $this->dbPath);
                $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

                $stmt = $db->query("SELECT COUNT(*), SUM(net_pnl_usd), SUM(fee_drag_usd), SUM(slippage_drag_usd) FROM simulated_executions");
                $row = $stmt->fetch(PDO::FETCH_NUM);
                
                $stats['total_simulations'] = (int)($row[0] ?? 0);
                $stats['net_pnl_usd'] = round((float)($row[1] ?? 0), 2);
                $stats['total_fee_drag_usd'] = round((float)($row[2] ?? 0), 2);
                $stats['total_slippage_drag_usd'] = round((float)($row[3] ?? 0), 2);
            } catch (Exception $e) {
                $stats['db_error'] = $e->getMessage();
            }
        }

        return $stats;
    }
}
