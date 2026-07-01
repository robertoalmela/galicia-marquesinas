<?php
// One-time script: add notes column to marquesinas_decisions
define('DB_HOST', 'localhost');
define('DB_NAME', '277621438wordpress20250320121608');
define('DB_USER', 'myrobertoa3d');
define('DB_PASS', 'Roberto.1993');

try {
    $pdo = new PDO("mysql:host=".DB_HOST.";dbname=".DB_NAME.";charset=utf8mb4", DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    ]);
    
    // Add notes column if not exists
    $pdo->exec("ALTER TABLE marquesinas_decisions ADD COLUMN notes TEXT DEFAULT NULL AFTER name");
    echo "Column 'notes' added successfully!";
} catch (PDOException $e) {
    if (strpos($e->getMessage(), 'Duplicate column') !== false) {
        echo "Column 'notes' already exists.";
    } else {
        echo "Error: " . $e->getMessage();
    }
}
?>