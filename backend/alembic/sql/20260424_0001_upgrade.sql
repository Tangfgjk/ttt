-- Alembic upgrade SQL for initial schema
-- Generated from docs/design/v2/01-init-schema-mysql.sql
-- Database selection should be handled by Alembic connection URL

-- V2 first-version MySQL schema
-- Target: MySQL 8.0+
-- Charset: utf8mb4




CREATE TABLE IF NOT EXISTS `subjects` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(32) NOT NULL,
  `name` VARCHAR(64) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_subjects_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `grades` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `grade_index` SMALLINT NOT NULL,
  `grade_code` VARCHAR(32) DEFAULT NULL,
  `grade_name` VARCHAR(64) NOT NULL,
  `edu_stage` VARCHAR(32) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_grades_grade_index` (`grade_index`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_types` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(64) NOT NULL,
  `name` VARCHAR(64) NOT NULL,
  `base_type_index` INT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_types_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cognitive_levels` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(32) NOT NULL,
  `name` VARCHAR(32) NOT NULL,
  `level_order` SMALLINT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cognitive_levels_code` (`code`),
  UNIQUE KEY `uk_cognitive_levels_order` (`level_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `competencies` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(64) NOT NULL,
  `name` VARCHAR(64) NOT NULL,
  `display_order` SMALLINT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_competencies_code` (`code`),
  UNIQUE KEY `uk_competencies_display_order` (`display_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `knowledge_types` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source_type_code` VARCHAR(64) NOT NULL,
  `source_type_name` VARCHAR(64) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_knowledge_types_source_type_code` (`source_type_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `textbooks` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source_textbook_id` VARCHAR(64) NOT NULL,
  `name` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_textbooks_source_textbook_id` (`source_textbook_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `roles` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(32) NOT NULL,
  `name` VARCHAR(64) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_roles_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `permissions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(64) NOT NULL,
  `name` VARCHAR(128) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_permissions_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `learning_modules` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(64) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `sort_order` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_learning_modules_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `data_sources` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(64) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `source_type` VARCHAR(32) NOT NULL,
  `description` VARCHAR(500) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_data_sources_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `embedding_models` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `model_code` VARCHAR(64) NOT NULL,
  `model_name` VARCHAR(128) NOT NULL,
  `dimension` SMALLINT NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_embedding_models_model_code` (`model_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `knowledge_points` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source_knowledge_id` VARCHAR(64) DEFAULT NULL,
  `knowledge_type_id` BIGINT UNSIGNED NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `parent_id` BIGINT UNSIGNED DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_knowledge_points_source_type` (`source_knowledge_id`, `knowledge_type_id`),
  KEY `idx_knowledge_points_parent_id` (`parent_id`),
  CONSTRAINT `fk_knowledge_points_knowledge_type_id`
    FOREIGN KEY (`knowledge_type_id`) REFERENCES `knowledge_types` (`id`),
  CONSTRAINT `fk_knowledge_points_parent_id`
    FOREIGN KEY (`parent_id`) REFERENCES `knowledge_points` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `catalogs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source_catalog_id` VARCHAR(64) DEFAULT NULL,
  `textbook_id` BIGINT UNSIGNED DEFAULT NULL,
  `parent_id` BIGINT UNSIGNED DEFAULT NULL,
  `name` VARCHAR(255) NOT NULL,
  `school_code` VARCHAR(32) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_catalogs_source_catalog_textbook` (`source_catalog_id`, `textbook_id`),
  KEY `idx_catalogs_parent_id` (`parent_id`),
  CONSTRAINT `fk_catalogs_textbook_id`
    FOREIGN KEY (`textbook_id`) REFERENCES `textbooks` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_catalogs_parent_id`
    FOREIGN KEY (`parent_id`) REFERENCES `catalogs` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `role_permissions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `role_id` BIGINT UNSIGNED NOT NULL,
  `permission_id` BIGINT UNSIGNED NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_permissions_role_permission` (`role_id`, `permission_id`),
  CONSTRAINT `fk_role_permissions_role_id`
    FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_role_permissions_permission_id`
    FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `users` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(64) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role_id` BIGINT UNSIGNED NOT NULL,
  `real_name` VARCHAR(64) DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `is_verified` TINYINT(1) NOT NULL DEFAULT 0,
  `last_login_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_username` (`username`),
  UNIQUE KEY `uk_users_email` (`email`),
  KEY `idx_users_role_id` (`role_id`),
  CONSTRAINT `fk_users_role_id`
    FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `learning_records` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `module_id` BIGINT UNSIGNED NOT NULL,
  `progress_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `is_completed` TINYINT(1) NOT NULL DEFAULT 0,
  `completed_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_learning_records_user_module` (`user_id`, `module_id`),
  CONSTRAINT `fk_learning_records_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_learning_records_module_id`
    FOREIGN KEY (`module_id`) REFERENCES `learning_modules` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `import_batches` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `data_source_id` BIGINT UNSIGNED NOT NULL,
  `batch_no` VARCHAR(64) NOT NULL,
  `file_name` VARCHAR(255) NOT NULL,
  `import_status` VARCHAR(32) NOT NULL,
  `total_records` INT UNSIGNED NOT NULL DEFAULT 0,
  `success_records` INT UNSIGNED NOT NULL DEFAULT 0,
  `failed_records` INT UNSIGNED NOT NULL DEFAULT 0,
  `error_message` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finished_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_import_batches_batch_no` (`batch_no`),
  KEY `idx_import_batches_data_source_id` (`data_source_id`),
  CONSTRAINT `fk_import_batches_data_source_id`
    FOREIGN KEY (`data_source_id`) REFERENCES `data_sources` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `source_question_records` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `import_batch_id` BIGINT UNSIGNED NOT NULL,
  `data_source_id` BIGINT UNSIGNED NOT NULL,
  `source_record_key` VARCHAR(128) NOT NULL,
  `record_type` VARCHAR(32) NOT NULL,
  `raw_payload` JSON NOT NULL,
  `normalized_hash` CHAR(64) DEFAULT NULL,
  `parse_status` VARCHAR(32) NOT NULL,
  `error_message` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_source_question_records_import_batch_id` (`import_batch_id`),
  KEY `idx_source_question_records_source_key` (`data_source_id`, `source_record_key`),
  CONSTRAINT `fk_source_question_records_import_batch_id`
    FOREIGN KEY (`import_batch_id`) REFERENCES `import_batches` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_source_question_records_data_source_id`
    FOREIGN KEY (`data_source_id`) REFERENCES `data_sources` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `questions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `subject_id` BIGINT UNSIGNED NOT NULL,
  `grade_id` BIGINT UNSIGNED DEFAULT NULL,
  `question_type_id` BIGINT UNSIGNED DEFAULT NULL,
  `difficulty_level` SMALLINT DEFAULT NULL,
  `blank_count` SMALLINT NOT NULL DEFAULT 0,
  `has_subquestions` TINYINT(1) NOT NULL DEFAULT 0,
  `source_status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
  `annotation_status` VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  `required_annotations` SMALLINT NOT NULL DEFAULT 3,
  `annotation_count` SMALLINT NOT NULL DEFAULT 0,
  `latest_embedding_version` VARCHAR(64) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_questions_subject_grade_status` (`subject_id`, `grade_id`, `annotation_status`),
  KEY `idx_questions_question_type_id` (`question_type_id`),
  CONSTRAINT `fk_questions_subject_id`
    FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`),
  CONSTRAINT `fk_questions_grade_id`
    FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_questions_question_type_id`
    FOREIGN KEY (`question_type_id`) REFERENCES `question_types` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_external_refs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `data_source_id` BIGINT UNSIGNED NOT NULL,
  `external_question_id` VARCHAR(128) NOT NULL,
  `external_type` VARCHAR(32) DEFAULT NULL,
  `is_primary` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_external_refs_source_external_id` (`data_source_id`, `external_question_id`),
  KEY `idx_question_external_refs_question_id` (`question_id`),
  CONSTRAINT `fk_question_external_refs_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_external_refs_data_source_id`
    FOREIGN KEY (`data_source_id`) REFERENCES `data_sources` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_contents` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `stem_text` LONGTEXT NOT NULL,
  `stem_html` LONGTEXT DEFAULT NULL,
  `answer_text` LONGTEXT DEFAULT NULL,
  `solution_text` LONGTEXT DEFAULT NULL,
  `source_content_hash` CHAR(64) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_contents_question_id` (`question_id`),
  CONSTRAINT `fk_question_contents_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_subquestions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `sub_no` SMALLINT NOT NULL,
  `stem_text` LONGTEXT DEFAULT NULL,
  `stem_html` LONGTEXT DEFAULT NULL,
  `answer_text` LONGTEXT DEFAULT NULL,
  `score` DECIMAL(6,2) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_subquestions_question_subno` (`question_id`, `sub_no`),
  CONSTRAINT `fk_question_subquestions_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_assets` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `subquestion_id` BIGINT UNSIGNED DEFAULT NULL,
  `asset_type` VARCHAR(32) NOT NULL,
  `asset_url` VARCHAR(500) NOT NULL,
  `storage_key` VARCHAR(255) DEFAULT NULL,
  `sort_order` SMALLINT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_question_assets_question_id` (`question_id`),
  KEY `idx_question_assets_subquestion_id` (`subquestion_id`),
  CONSTRAINT `fk_question_assets_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_assets_subquestion_id`
    FOREIGN KEY (`subquestion_id`) REFERENCES `question_subquestions` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_knowledge_points` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `knowledge_point_id` BIGINT UNSIGNED NOT NULL,
  `priority` SMALLINT NOT NULL DEFAULT 0,
  `is_core` TINYINT(1) NOT NULL DEFAULT 0,
  `is_exam_point` TINYINT(1) NOT NULL DEFAULT 0,
  `is_last_exam_point` TINYINT(1) NOT NULL DEFAULT 0,
  `sort_index` INT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_knowledge_points_question_knowledge` (`question_id`, `knowledge_point_id`),
  CONSTRAINT `fk_question_knowledge_points_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_knowledge_points_knowledge_point_id`
    FOREIGN KEY (`knowledge_point_id`) REFERENCES `knowledge_points` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_catalogs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `catalog_id` BIGINT UNSIGNED NOT NULL,
  `school_code` VARCHAR(32) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_catalogs_question_catalog` (`question_id`, `catalog_id`),
  CONSTRAINT `fk_question_catalogs_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_catalogs_catalog_id`
    FOREIGN KEY (`catalog_id`) REFERENCES `catalogs` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_gold_labels` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `source_record_id` BIGINT UNSIGNED DEFAULT NULL,
  `cognitive_level_id` BIGINT UNSIGNED DEFAULT NULL,
  `label_source` VARCHAR(64) NOT NULL,
  `imported_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_gold_labels_question_id` (`question_id`),
  CONSTRAINT `fk_question_gold_labels_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_gold_labels_source_record_id`
    FOREIGN KEY (`source_record_id`) REFERENCES `source_question_records` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_question_gold_labels_cognitive_level_id`
    FOREIGN KEY (`cognitive_level_id`) REFERENCES `cognitive_levels` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_gold_competencies` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `gold_label_id` BIGINT UNSIGNED NOT NULL,
  `competency_id` BIGINT UNSIGNED NOT NULL,
  `level_value` SMALLINT NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_gold_competencies_label_competency` (`gold_label_id`, `competency_id`),
  CONSTRAINT `fk_question_gold_competencies_gold_label_id`
    FOREIGN KEY (`gold_label_id`) REFERENCES `question_gold_labels` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_gold_competencies_competency_id`
    FOREIGN KEY (`competency_id`) REFERENCES `competencies` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `classes` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source_class_id` VARCHAR(64) DEFAULT NULL,
  `grade_id` BIGINT UNSIGNED DEFAULT NULL,
  `class_name` VARCHAR(128) NOT NULL,
  `class_seq` SMALLINT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_classes_source_class_grade` (`source_class_id`, `grade_id`),
  CONSTRAINT `fk_classes_grade_id`
    FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `students` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source_student_id` VARCHAR(64) NOT NULL,
  `student_name` VARCHAR(128) DEFAULT NULL,
  `grade_id` BIGINT UNSIGNED DEFAULT NULL,
  `class_id` BIGINT UNSIGNED DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_students_source_student_id` (`source_student_id`),
  CONSTRAINT `fk_students_grade_id`
    FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_students_class_id`
    FOREIGN KEY (`class_id`) REFERENCES `classes` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `exams` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source_exam_id` VARCHAR(64) NOT NULL,
  `exam_code` VARCHAR(64) DEFAULT NULL,
  `exam_name` VARCHAR(255) NOT NULL,
  `subject_id` BIGINT UNSIGNED DEFAULT NULL,
  `grade_id` BIGINT UNSIGNED DEFAULT NULL,
  `exam_type` VARCHAR(64) DEFAULT NULL,
  `term_name` VARCHAR(64) DEFAULT NULL,
  `exam_time` DATETIME DEFAULT NULL,
  `total_score` DECIMAL(8,2) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_exams_source_exam_id` (`source_exam_id`),
  CONSTRAINT `fk_exams_subject_id`
    FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_exams_grade_id`
    FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `exam_questions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `exam_id` BIGINT UNSIGNED NOT NULL,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `question_no` VARCHAR(32) DEFAULT NULL,
  `custom_question_no` VARCHAR(32) DEFAULT NULL,
  `score` DECIMAL(6,2) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_exam_questions_exam_question` (`exam_id`, `question_id`),
  CONSTRAINT `fk_exam_questions_exam_id`
    FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_exam_questions_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `student_exam_scores` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `exam_id` BIGINT UNSIGNED NOT NULL,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `class_id` BIGINT UNSIGNED DEFAULT NULL,
  `total_score` DECIMAL(8,2) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_exam_scores_exam_student` (`exam_id`, `student_id`),
  CONSTRAINT `fk_student_exam_scores_exam_id`
    FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_student_exam_scores_student_id`
    FOREIGN KEY (`student_id`) REFERENCES `students` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_student_exam_scores_class_id`
    FOREIGN KEY (`class_id`) REFERENCES `classes` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `student_question_responses` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `exam_id` BIGINT UNSIGNED NOT NULL,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `response_text` LONGTEXT DEFAULT NULL,
  `response_score` DECIMAL(6,2) DEFAULT NULL,
  `subquestion_answer_text` LONGTEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_question_responses_exam_question_student` (`exam_id`, `question_id`, `student_id`),
  KEY `idx_student_question_responses_question_id` (`question_id`),
  CONSTRAINT `fk_student_question_responses_exam_id`
    FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_student_question_responses_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_student_question_responses_student_id`
    FOREIGN KEY (`student_id`) REFERENCES `students` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `recommendation_batches` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `batch_no` VARCHAR(64) NOT NULL,
  `algorithm_code` VARCHAR(64) NOT NULL,
  `triggered_by_user_id` BIGINT UNSIGNED DEFAULT NULL,
  `target_stage` VARCHAR(32) DEFAULT NULL,
  `context_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_recommendation_batches_batch_no` (`batch_no`),
  KEY `idx_recommendation_batches_triggered_by_user_id` (`triggered_by_user_id`),
  CONSTRAINT `fk_recommendation_batches_triggered_by_user_id`
    FOREIGN KEY (`triggered_by_user_id`) REFERENCES `users` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `annotation_tasks` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `assignee_id` BIGINT UNSIGNED NOT NULL,
  `source_batch_id` BIGINT UNSIGNED DEFAULT NULL,
  `task_status` VARCHAR(32) NOT NULL,
  `assigned_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` DATETIME DEFAULT NULL,
  `submitted_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_annotation_tasks_question_assignee_status` (`question_id`, `assignee_id`, `task_status`),
  KEY `idx_annotation_tasks_source_batch_id` (`source_batch_id`),
  CONSTRAINT `fk_annotation_tasks_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_annotation_tasks_assignee_id`
    FOREIGN KEY (`assignee_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_annotation_tasks_source_batch_id`
    FOREIGN KEY (`source_batch_id`) REFERENCES `recommendation_batches` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `annotations` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `task_id` BIGINT UNSIGNED DEFAULT NULL,
  `version_no` SMALLINT NOT NULL DEFAULT 1,
  `cognitive_level_id` BIGINT UNSIGNED DEFAULT NULL,
  `confidence_level` SMALLINT DEFAULT NULL,
  `time_spent_seconds` INT DEFAULT NULL,
  `is_final` TINYINT(1) NOT NULL DEFAULT 0,
  `annotation_status` VARCHAR(32) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_annotations_question_user_version` (`question_id`, `user_id`, `version_no`),
  KEY `idx_annotations_task_id` (`task_id`),
  CONSTRAINT `fk_annotations_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_annotations_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_annotations_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `annotation_tasks` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_annotations_cognitive_level_id`
    FOREIGN KEY (`cognitive_level_id`) REFERENCES `cognitive_levels` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `annotation_competencies` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `annotation_id` BIGINT UNSIGNED NOT NULL,
  `competency_id` BIGINT UNSIGNED NOT NULL,
  `level_value` SMALLINT NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_annotation_competencies_annotation_competency` (`annotation_id`, `competency_id`),
  CONSTRAINT `fk_annotation_competencies_annotation_id`
    FOREIGN KEY (`annotation_id`) REFERENCES `annotations` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_annotation_competencies_competency_id`
    FOREIGN KEY (`competency_id`) REFERENCES `competencies` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `annotation_knowledge_points` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `annotation_id` BIGINT UNSIGNED NOT NULL,
  `knowledge_point_id` BIGINT UNSIGNED NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_annotation_kps_annotation_kp` (`annotation_id`, `knowledge_point_id`),
  CONSTRAINT `fk_annotation_knowledge_points_annotation_id`
    FOREIGN KEY (`annotation_id`) REFERENCES `annotations` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_annotation_knowledge_points_knowledge_point_id`
    FOREIGN KEY (`knowledge_point_id`) REFERENCES `knowledge_points` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_label_aggregates` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `final_cognitive_level_id` BIGINT UNSIGNED DEFAULT NULL,
  `agreement_score` DECIMAL(5,2) DEFAULT NULL,
  `is_disputed` TINYINT(1) NOT NULL DEFAULT 0,
  `completed_annotation_count` SMALLINT NOT NULL DEFAULT 0,
  `finalized_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_label_aggregates_question_id` (`question_id`),
  CONSTRAINT `fk_question_label_aggregates_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_label_aggregates_final_cognitive_level_id`
    FOREIGN KEY (`final_cognitive_level_id`) REFERENCES `cognitive_levels` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_aggregate_competencies` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `aggregate_id` BIGINT UNSIGNED NOT NULL,
  `competency_id` BIGINT UNSIGNED NOT NULL,
  `level_value` SMALLINT NOT NULL DEFAULT 1,
  `agreement_score` DECIMAL(5,2) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_aggregate_competencies_aggregate_competency` (`aggregate_id`, `competency_id`),
  CONSTRAINT `fk_question_aggregate_competencies_aggregate_id`
    FOREIGN KEY (`aggregate_id`) REFERENCES `question_label_aggregates` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_aggregate_competencies_competency_id`
    FOREIGN KEY (`competency_id`) REFERENCES `competencies` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `review_tasks` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `aggregate_id` BIGINT UNSIGNED NOT NULL,
  `reviewer_id` BIGINT UNSIGNED DEFAULT NULL,
  `review_status` VARCHAR(32) NOT NULL,
  `review_comment` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `reviewed_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_review_tasks_reviewer_id` (`reviewer_id`),
  CONSTRAINT `fk_review_tasks_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_review_tasks_aggregate_id`
    FOREIGN KEY (`aggregate_id`) REFERENCES `question_label_aggregates` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_review_tasks_reviewer_id`
    FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_embeddings` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `embedding_model_id` BIGINT UNSIGNED NOT NULL,
  `vector_json` JSON NOT NULL,
  `vector_norm` DECIMAL(12,6) DEFAULT NULL,
  `computed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_embeddings_question_model` (`question_id`, `embedding_model_id`),
  CONSTRAINT `fk_question_embeddings_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_question_embeddings_embedding_model_id`
    FOREIGN KEY (`embedding_model_id`) REFERENCES `embedding_models` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `recommendation_items` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `batch_id` BIGINT UNSIGNED NOT NULL,
  `question_id` BIGINT UNSIGNED NOT NULL,
  `score` DECIMAL(14,6) NOT NULL,
  `rank_no` INT NOT NULL,
  `is_accepted` TINYINT(1) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_recommendation_items_batch_question` (`batch_id`, `question_id`),
  KEY `idx_recommendation_items_question_id` (`question_id`),
  CONSTRAINT `fk_recommendation_items_batch_id`
    FOREIGN KEY (`batch_id`) REFERENCES `recommendation_batches` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_recommendation_items_question_id`
    FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `coreset_experiments` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `batch_id` BIGINT UNSIGNED NOT NULL,
  `algorithm_code` VARCHAR(64) NOT NULL,
  `params_json` JSON DEFAULT NULL,
  `metrics_json` JSON DEFAULT NULL,
  `selected_question_count` INT UNSIGNED NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_coreset_experiments_batch_id` (`batch_id`),
  CONSTRAINT `fk_coreset_experiments_batch_id`
    FOREIGN KEY (`batch_id`) REFERENCES `recommendation_batches` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `model_versions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `version_code` VARCHAR(64) NOT NULL,
  `model_type` VARCHAR(64) NOT NULL,
  `base_model_name` VARCHAR(128) DEFAULT NULL,
  `artifact_path` VARCHAR(255) DEFAULT NULL,
  `metrics_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_versions_version_code` (`version_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `training_datasets` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `dataset_code` VARCHAR(64) NOT NULL,
  `sample_count` INT UNSIGNED NOT NULL DEFAULT 0,
  `dataset_config_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_training_datasets_dataset_code` (`dataset_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `training_tasks` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `task_no` VARCHAR(64) NOT NULL,
  `dataset_id` BIGINT UNSIGNED NOT NULL,
  `model_version_id` BIGINT UNSIGNED DEFAULT NULL,
  `task_status` VARCHAR(32) NOT NULL,
  `queue_name` VARCHAR(64) DEFAULT NULL,
  `celery_task_id` VARCHAR(128) DEFAULT NULL,
  `hyperparams_json` JSON DEFAULT NULL,
  `metrics_json` JSON DEFAULT NULL,
  `created_by` BIGINT UNSIGNED DEFAULT NULL,
  `started_at` DATETIME DEFAULT NULL,
  `finished_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_training_tasks_task_no` (`task_no`),
  KEY `idx_training_tasks_dataset_id` (`dataset_id`),
  CONSTRAINT `fk_training_tasks_dataset_id`
    FOREIGN KEY (`dataset_id`) REFERENCES `training_datasets` (`id`),
  CONSTRAINT `fk_training_tasks_model_version_id`
    FOREIGN KEY (`model_version_id`) REFERENCES `model_versions` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_training_tasks_created_by`
    FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED DEFAULT NULL,
  `module_code` VARCHAR(64) NOT NULL,
  `action_code` VARCHAR(64) NOT NULL,
  `target_type` VARCHAR(64) DEFAULT NULL,
  `target_id` VARCHAR(128) DEFAULT NULL,
  `detail_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_logs_user_id` (`user_id`),
  KEY `idx_audit_logs_module_action` (`module_code`, `action_code`),
  CONSTRAINT `fk_audit_logs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Minimal seed data
INSERT INTO `subjects` (`code`, `name`)
VALUES ('math', '数学')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

INSERT INTO `grades` (`grade_index`, `grade_code`, `grade_name`, `edu_stage`)
VALUES
  (7, 'grade_7', '七年级', 'junior'),
  (8, 'grade_8', '八年级', 'junior'),
  (9, 'grade_9', '九年级', 'junior'),
  (10, 'grade_10', '高一', 'senior'),
  (11, 'grade_11', '高二', 'senior'),
  (12, 'grade_12', '高三', 'senior')
ON DUPLICATE KEY UPDATE
  `grade_code` = VALUES(`grade_code`),
  `grade_name` = VALUES(`grade_name`),
  `edu_stage` = VALUES(`edu_stage`);

INSERT INTO `cognitive_levels` (`code`, `name`, `level_order`)
VALUES
  ('remember', '识记', 1),
  ('understand', '理解', 2),
  ('apply', '应用', 3),
  ('analyze', '分析', 4),
  ('synthesize', '综合', 5),
  ('evaluate', '评价', 6)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `level_order` = VALUES(`level_order`);

INSERT INTO `competencies` (`code`, `name`, `display_order`)
VALUES
  ('abstraction', '抽象能力', 1),
  ('operation', '运算能力', 2),
  ('geometric_intuition', '几何直观', 3),
  ('spatial_conception', '空间观念', 4),
  ('reasoning', '推理能力', 5),
  ('data_consciousness', '数据观念', 6),
  ('model_consciousness', '模型观念', 7),
  ('application_awareness', '应用意识', 8),
  ('innovation_awareness', '创新意识', 9),
  ('mathematical_abstraction', '数学抽象', 10),
  ('logical_reasoning', '逻辑推理', 11),
  ('mathematical_modeling', '数学建模', 12),
  ('intuitive_imagination', '直观想象', 13),
  ('mathematical_operation', '数学运算', 14),
  ('data_analysis', '数据分析', 15)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `display_order` = VALUES(`display_order`);

INSERT INTO `roles` (`code`, `name`)
VALUES
  ('admin', '管理员'),
  ('annotator', '标注员'),
  ('reviewer', '复核员'),
  ('viewer', '只读用户')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

INSERT INTO `question_types` (`code`, `name`, `base_type_index`)
VALUES
  ('single_choice', '单选题', 1),
  ('fill_blank', '填空题', 2),
  ('essay', '解答题', 3),
  ('select_single', '单选题(来源枚举)', 1)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `base_type_index` = VALUES(`base_type_index`);

INSERT INTO `knowledge_types` (`source_type_code`, `source_type_name`)
VALUES
  ('knowledge_point', '知识点'),
  ('exam_point', '考点'),
  ('question_pattern', '题型')
ON DUPLICATE KEY UPDATE `source_type_name` = VALUES(`source_type_name`);

INSERT INTO `data_sources` (`code`, `name`, `source_type`, `description`)
VALUES
  ('dataset1_labeled', '数据集1-已标注题库', 'excel', '来自初中.xlsx 的已标注题目样例'),
  ('dataset2_question_json', '数据集2-题目元数据', 'json', '来自单题 JSON 的题目元数据样例'),
  ('dataset3_exam_sheet', '数据集3-考试作答明细', 'excel', '来自工作簿1.xlsx 的考试与作答样例')
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `source_type` = VALUES(`source_type`),
  `description` = VALUES(`description`);
