-- Definitive Database Schema for School Transport Management System
-- Updated: 2026-02-26

CREATE TABLE IF NOT EXISTS `routes` (
  `route_id` char(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `routes_active_status` varchar(20) DEFAULT 'ACTIVE',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`route_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `drivers` (
  `driver_id` char(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `phone` bigint NOT NULL,
  `email` varchar(150) DEFAULT NULL,
  `licence_number` varchar(50) DEFAULT NULL,
  `licence_expiry` date DEFAULT NULL,
  `password_hash` varchar(200) DEFAULT NULL,
  `fcm_token` varchar(255) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'ACTIVE',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`driver_id`),
  UNIQUE KEY `phone` (`phone`),
  CONSTRAINT `drivers_chk_1` CHECK ((`phone` between 1000000000 and 9999999999))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `admins` (
  `admin_id` char(36) NOT NULL,
  `phone` bigint NOT NULL,
  `email` varchar(150) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(100) NOT NULL,
  `status` varchar(20) DEFAULT 'ACTIVE',
  `last_login_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `phone` (`phone`),
  UNIQUE KEY `email` (`email`),
  CONSTRAINT `admins_chk_1` CHECK ((`phone` between 1000000000 and 9999999999))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `parents` (
  `parent_id` char(36) NOT NULL,
  `phone` bigint NOT NULL,
  `email` varchar(150) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(100) NOT NULL,
  `parent_role` enum('FATHER','MOTHER','GUARDIAN') DEFAULT 'GUARDIAN',
  `door_no` varchar(50) DEFAULT NULL,
  `street` varchar(100) DEFAULT NULL,
  `city` varchar(50) DEFAULT NULL,
  `district` varchar(50) DEFAULT NULL,
  `pincode` varchar(10) DEFAULT NULL,
  `last_login_at` timestamp NULL DEFAULT NULL,
  `parents_active_status` varchar(20) DEFAULT 'ACTIVE',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`parent_id`),
  UNIQUE KEY `phone` (`phone`),
  UNIQUE KEY `email` (`email`),
  CONSTRAINT `parents_chk_1` CHECK ((`phone` between 1000000000 and 9999999999))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `buses` (
  `bus_id` char(36) NOT NULL,
  `registration_number` varchar(20) NOT NULL,
  `driver_id` char(36) DEFAULT NULL,
  `route_id` char(36) DEFAULT NULL,
  `vehicle_type` varchar(50) DEFAULT NULL,
  `bus_brand` varchar(100) DEFAULT NULL,
  `bus_model` varchar(100) DEFAULT NULL,
  `seating_capacity` int NOT NULL,
  `rc_expiry_date` date DEFAULT NULL,
  `fc_expiry_date` date DEFAULT NULL,
  `rc_book_url` varchar(255) DEFAULT NULL,
  `fc_certificate_url` varchar(255) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'ACTIVE',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `bus_name` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`bus_id`),
  UNIQUE KEY `registration_number` (`registration_number`),
  KEY `driver_id` (`driver_id`),
  KEY `route_id` (`route_id`),
  CONSTRAINT `buses_ibfk_1` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`driver_id`),
  CONSTRAINT `buses_ibfk_2` FOREIGN KEY (`route_id`) REFERENCES `routes` (`route_id`),
  CONSTRAINT `buses_chk_1` CHECK ((`seating_capacity` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `classes` (
  `class_id` char(36) NOT NULL,
  `class_name` varchar(20) NOT NULL,
  `section` varchar(10) NOT NULL,
  `status` varchar(20) DEFAULT 'ACTIVE',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`class_id`),
  UNIQUE KEY `class_name` (`class_name`,`section`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `route_stops` (
  `stop_id` char(36) NOT NULL,
  `route_id` char(36) NOT NULL,
  `stop_name` varchar(100) NOT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `pickup_stop_order` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `drop_stop_order` int NOT NULL,
  PRIMARY KEY (`stop_id`),
  UNIQUE KEY `route_id` (`route_id`,`pickup_stop_order`),
  KEY `idx_route_order` (`route_id`,`pickup_stop_order`),
  CONSTRAINT `route_stops_ibfk_1` FOREIGN KEY (`route_id`) REFERENCES `routes` (`route_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `students` (
  `student_id` char(36) NOT NULL,
  `parent_id` char(36) NOT NULL,
  `s_parent_id` char(36) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `gender` enum('MALE','FEMALE','OTHER') NOT NULL,
  `dob` date DEFAULT NULL,
  `study_year` varchar(20) NOT NULL,
  `class_id` char(36) DEFAULT NULL,
  `pickup_route_id` char(36) NOT NULL,
  `drop_route_id` char(36) NOT NULL,
  `pickup_stop_id` char(36) NOT NULL,
  `drop_stop_id` char(36) NOT NULL,
  `student_status` varchar(50) DEFAULT 'ACTIVE',
  `transport_status` varchar(20) DEFAULT 'ACTIVE',
  `is_transport_user` tinyint(1) DEFAULT '1',
  `emergency_contact` bigint DEFAULT NULL,
  `student_photo_url` varchar(200) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`student_id`),
  KEY `parent_id` (`parent_id`),
  KEY `s_parent_id` (`s_parent_id`),
  KEY `class_id` (`class_id`),
  KEY `drop_route_id` (`drop_route_id`),
  KEY `drop_stop_id` (`drop_stop_id`),
  CONSTRAINT `students_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `parents` (`parent_id`),
  CONSTRAINT `students_ibfk_2` FOREIGN KEY (`s_parent_id`) REFERENCES `parents` (`parent_id`),
  CONSTRAINT `students_ibfk_3` FOREIGN KEY (`class_id`) REFERENCES `classes` (`class_id`),
  CONSTRAINT `students_ibfk_4` FOREIGN KEY (`pickup_route_id`) REFERENCES `routes` (`route_id`),
  CONSTRAINT `students_ibfk_5` FOREIGN KEY (`drop_route_id`) REFERENCES `routes` (`route_id`),
  CONSTRAINT `students_ibfk_6` FOREIGN KEY (`pickup_stop_id`) REFERENCES `route_stops` (`stop_id`),
  CONSTRAINT `students_ibfk_7` FOREIGN KEY (`drop_stop_id`) REFERENCES `route_stops` (`stop_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `trips` (
  `trip_id` char(36) NOT NULL,
  `bus_id` char(36) NOT NULL,
  `driver_id` char(36) NOT NULL,
  `route_id` char(36) NOT NULL,
  `trip_date` date NOT NULL,
  `trip_type` enum('PICKUP','DROP') NOT NULL,
  `status` enum('NOT_STARTED','ONGOING','PAUSED','COMPLETED','CANCELED') DEFAULT 'NOT_STARTED',
  `current_stop_order` int DEFAULT '0',
  `first_stop_notified` tinyint(1) DEFAULT '0',
  `started_at` timestamp NULL DEFAULT NULL,
  `ended_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`trip_id`),
  KEY `driver_id` (`driver_id`),
  KEY `idx_trips_bus_date` (`bus_id`,`trip_date`),
  KEY `idx_trips_route_status` (`route_id`,`status`),
  CONSTRAINT `trips_ibfk_1` FOREIGN KEY (`bus_id`) REFERENCES `buses` (`bus_id`),
  CONSTRAINT `trips_ibfk_2` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`driver_id`),
  CONSTRAINT `trips_ibfk_3` FOREIGN KEY (`route_id`) REFERENCES `routes` (`route_id`),
  CONSTRAINT `trips_chk_1` CHECK (((`ended_at` is null) or (`ended_at` > `started_at`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `fcm_tokens` (
  `fcm_id` char(36) NOT NULL,
  `fcm_token` varchar(255) NOT NULL,
  `student_id` char(36) DEFAULT NULL,
  `parent_id` char(36) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`fcm_id`),
  UNIQUE KEY `fcm_token` (`fcm_token`),
  UNIQUE KEY `idx_unique_parent_fcm` (`parent_id`),
  KEY `student_id` (`student_id`),
  KEY `parent_id` (`parent_id`),
  CONSTRAINT `fcm_tokens_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  CONSTRAINT `fcm_tokens_ibfk_2` FOREIGN KEY (`parent_id`) REFERENCES `parents` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `driver_live_locations` (
  `driver_id` char(36) NOT NULL,
  `latitude` decimal(10,7) NOT NULL,
  `longitude` decimal(10,7) NOT NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`driver_id`),
  CONSTRAINT `fk_driver_live_location` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`driver_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `route_stop_fcm_cache` (
  `route_id` char(36) NOT NULL,
  `stop_fcm_map` json NOT NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`route_id`),
  CONSTRAINT `route_stop_fcm_cache_ibfk_1` FOREIGN KEY (`route_id`) REFERENCES `routes` (`route_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `error_handling` (
  `error_id` char(36) NOT NULL,
  `error_type` varchar(50) DEFAULT NULL,
  `error_code` int DEFAULT NULL,
  `error_description` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`error_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
