-- Service Categories Seed Data
-- 9 top-level categories with subcategories

-- 1. Engineering & Design
INSERT INTO service_categories (name, parent_id, description) VALUES ('Engineering & Design', NULL, 'Engineering and design services for nuclear facilities');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Nuclear Engineering', 1, 'Core nuclear engineering services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Civil/Structural Engineering', 1, 'Civil and structural engineering for nuclear facilities');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Mechanical Engineering', 1, 'Mechanical systems engineering');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Electrical Engineering', 1, 'Electrical systems engineering');
INSERT INTO service_categories (name, parent_id, description) VALUES ('I&C Engineering', 1, 'Instrumentation and controls engineering');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Seismic Analysis', 1, 'Seismic qualification and analysis');

-- 2. Construction & Fabrication
INSERT INTO service_categories (name, parent_id, description) VALUES ('Construction & Fabrication', NULL, 'Construction and fabrication services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('General Construction', 8, 'General nuclear construction');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Modular Construction', 8, 'Modular and prefabricated construction');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Heavy Component Fabrication', 8, 'Fabrication of large nuclear components');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Welding & NDE', 8, 'Welding and non-destructive examination');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Concrete & Rebar', 8, 'Concrete placement and reinforcement');

-- 3. Operations & Maintenance
INSERT INTO service_categories (name, parent_id, description) VALUES ('Operations & Maintenance', NULL, 'Plant operations and maintenance services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Plant Operations', 14, 'Day-to-day plant operations support');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Outage Management', 14, 'Planned and forced outage management');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Maintenance Services', 14, 'Preventive and corrective maintenance');
INSERT INTO service_categories (name, parent_id, description) VALUES ('In-Service Inspection', 14, 'In-service inspection programs');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Chemistry Services', 14, 'Water chemistry and radiochemistry');

-- 4. Fuel Cycle Services
INSERT INTO service_categories (name, parent_id, description) VALUES ('Fuel Cycle Services', NULL, 'Nuclear fuel cycle services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Uranium Mining & Milling', 20, 'Uranium extraction and processing');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Conversion & Enrichment', 20, 'Uranium conversion and enrichment');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Fuel Fabrication', 20, 'Nuclear fuel assembly fabrication');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Spent Fuel Management', 20, 'Spent fuel storage and transportation');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Fuel Performance Analysis', 20, 'Fuel performance monitoring and analysis');

-- 5. Decommissioning & Waste Management
INSERT INTO service_categories (name, parent_id, description) VALUES ('Decommissioning & Waste Management', NULL, 'Decommissioning and radioactive waste services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Decommissioning Planning', 26, 'Decommissioning strategy and planning');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Dismantlement', 26, 'Physical dismantlement of nuclear facilities');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Waste Processing', 26, 'Radioactive waste processing and packaging');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Site Remediation', 26, 'Radiological site remediation and restoration');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Waste Transportation', 26, 'Radioactive waste transportation services');

-- 6. Licensing & Regulatory
INSERT INTO service_categories (name, parent_id, description) VALUES ('Licensing & Regulatory', NULL, 'NRC licensing and regulatory compliance services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('New Plant Licensing', 32, 'COL and ESP applications');
INSERT INTO service_categories (name, parent_id, description) VALUES ('License Renewal', 32, 'Operating license renewal applications');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Regulatory Compliance', 32, 'Ongoing regulatory compliance support');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Safety Analysis', 32, 'Safety analysis reports and reviews');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Environmental Services', 32, 'Environmental impact assessments');

-- 7. Radiation Protection & Health Physics
INSERT INTO service_categories (name, parent_id, description) VALUES ('Radiation Protection & Health Physics', NULL, 'Radiation protection and health physics services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Dosimetry', 38, 'Personnel and area dosimetry services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('ALARA Programs', 38, 'ALARA program development and implementation');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Radiological Surveys', 38, 'Radiological characterization and surveys');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Emergency Preparedness', 38, 'Emergency planning and preparedness');

-- 8. Information Technology & Digital
INSERT INTO service_categories (name, parent_id, description) VALUES ('Information Technology & Digital', NULL, 'IT and digital services for nuclear facilities');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Cybersecurity', 43, 'Nuclear cybersecurity programs');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Digital I&C', 43, 'Digital instrumentation and control systems');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Data Analytics', 43, 'Data analytics and predictive maintenance');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Plant Simulators', 43, 'Full-scope and engineering simulators');

-- 9. Consulting & Advisory
INSERT INTO service_categories (name, parent_id, description) VALUES ('Consulting & Advisory', NULL, 'Consulting and advisory services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Financial Advisory', 48, 'Financial and investment advisory');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Legal Services', 48, 'Nuclear energy legal services');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Public Affairs', 48, 'Public affairs and community engagement');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Workforce Development', 48, 'Training and workforce development');
INSERT INTO service_categories (name, parent_id, description) VALUES ('Strategic Planning', 48, 'Strategic planning and market analysis');
