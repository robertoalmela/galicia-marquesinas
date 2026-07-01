-- Tabla de decisiones persistente para marquesinas de Galicia
CREATE TABLE IF NOT EXISTS marquesinas_decisions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  stop_id VARCHAR(50) NOT NULL UNIQUE,
  decision ENUM('kept', 'removed') NOT NULL,
  lat DECIMAL(10,7),
  lng DECIMAL(10,7),
  name VARCHAR(255),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_stop_id (stop_id),
  INDEX idx_updated_at (updated_at),
  INDEX idx_decision (decision)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
