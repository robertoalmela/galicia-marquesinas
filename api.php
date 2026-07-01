<?php
/**
 * API para Marquesinas de Galicia
 * GET  /api.php?action=get    → Devuelve todas las decisiones
 * POST /api.php?action=save   → Guarda una decisión (kept/removed) con notas opcionales
 * POST /api.php?action=delete → Elimina una decisión (vuelve a pendiente)
 * GET  /api.php?action=poll&since=TIMESTAMP → Cambios desde un timestamp
 */

// --- Config ---
define('DB_HOST', 'localhost');
define('DB_NAME', '277621438wordpress20250320121608');
define('DB_USER', 'myrobertoa3d');
define('DB_PASS', 'Roberto.1993');
define('DB_CHARSET', 'utf8mb4');

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// --- DB ---
function getDB(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $pdo = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET,
                DB_USER, DB_PASS, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ]);
        } catch (PDOException $e) {
            http_response_code(500);
            echo json_encode(['error' => 'Database connection failed']);
            exit;
        }
    }
    return $pdo;
}

// --- JSON helper ---
function json(array $data, int $code = 200): void {
    http_response_code($code);
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

// --- Router ---
$action = $_GET['action'] ?? '';

try {
    $db = getDB();

    switch ($action) {
        case 'get':
            // Devuelve todas las decisiones (kept con info, removed solo IDs)
            $kept = $db->query("SELECT stop_id, lat, lng, name, notes, updated_at FROM marquesinas_decisions WHERE decision = 'kept'")->fetchAll();
            $removed = $db->query("SELECT stop_id, notes FROM marquesinas_decisions WHERE decision = 'removed'")->fetchAll(PDO::FETCH_ASSOC);
            json([
                'kept' => $kept,
                'removed' => $removed,
            ]);
            break;

        case 'save':
            // Guarda o actualiza una decisión (con notas opcionales)
            $input = json_decode(file_get_contents('php://input'), true);
            if (!$input || empty($input['stop_id']) || empty($input['decision'])) {
                json(['error' => 'stop_id and decision required'], 400);
            }
            $decision = $input['decision'];
            if (!in_array($decision, ['kept', 'removed'])) {
                json(['error' => 'decision must be kept or removed'], 400);
            }

            $stmt = $db->prepare("
                INSERT INTO marquesinas_decisions (stop_id, decision, lat, lng, name, notes)
                VALUES (:stop_id, :decision, :lat, :lng, :name, :notes)
                ON DUPLICATE KEY UPDATE
                    decision = VALUES(decision),
                    lat = VALUES(lat),
                    lng = VALUES(lng),
                    name = VALUES(name),
                    notes = VALUES(notes),
                    updated_at = NOW()
            ");
            $stmt->execute([
                ':stop_id' => $input['stop_id'],
                ':decision' => $decision,
                ':lat' => $input['lat'] ?? null,
                ':lng' => $input['lng'] ?? null,
                ':name' => $input['name'] ?? '',
                ':notes' => $input['notes'] ?? null,
            ]);

            json(['ok' => true, 'stop_id' => $input['stop_id'], 'decision' => $decision]);
            break;

        case 'delete':
            // Elimina una decisión (vuelve a pendiente)
            $input = json_decode(file_get_contents('php://input'), true);
            if (!$input || empty($input['stop_id'])) {
                json(['error' => 'stop_id required'], 400);
            }
            $stmt = $db->prepare("DELETE FROM marquesinas_decisions WHERE stop_id = :stop_id");
            $stmt->execute([':stop_id' => $input['stop_id']]);
            json(['ok' => true, 'stop_id' => $input['stop_id']]);
            break;

        case 'poll':
            // Devuelve decisiones actualizadas desde un timestamp
            $since = $_GET['since'] ?? '1970-01-01 00:00:00';
            $stmt = $db->prepare("SELECT stop_id, decision, lat, lng, name, notes, updated_at FROM marquesinas_decisions WHERE updated_at > :since");
            $stmt->execute([':since' => $since]);
            $changes = $stmt->fetchAll();
            json(['changes' => $changes, 'server_time' => date('Y-m-d H:i:s')]);
            break;

        default:
            json(['error' => 'Unknown action. Use: get, save, delete, poll'], 400);
    }

} catch (Exception $e) {
    json(['error' => $e->getMessage()], 500);
}