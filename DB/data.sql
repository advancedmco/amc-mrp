-- =============================================
-- SAMPLE DATA INSERTS
-- =============================================

-- Insert sample customers
INSERT INTO Customers (CustomerName, QuickBooksID) VALUES
('Relli Technology Inc.', 'QB_RELLI_001'),
('Shibaura Machine Co, America', 'QB_SHIBAURA_001'),
('Trim-Tex, Inc.','QB_TRIMTEX_001');

-- Insert sample vendors
INSERT INTO Vendors (VendorName, QuickBooksID, ContactPhone, ContactEmail, Address) VALUES
('Expert Metal Finishing Inc', 'QB_EXPERT_001', '708-583-2550', 'expertmetalfinish@sbcglobal.net', '2120 West St, River Grove IL 60171'),
('General Surface Hardening', 'QB_GSH_001', '312-226-5472', 'ar@gshinc.net', 'PO Box 454, Lemont IL 60439'),
('Nova-Chrome Inc', 'QB_NOVA_001', '847-455-8200', 'Kevin@nova-chrome.com', '3200 N Wolf Rd, Franklin Park IL 60131'),
('Precise Rotary Die Inc.', 'QB_PRECISE_001', '847-678-0001', 'ioana@preciserotarydie.com', '3503 Martens St, Franklin Park IL 60131');

-- Insert sample parts
INSERT INTO Parts (PartNumber, PartName, Description, Material, DrawingNumber, FSN) VALUES
('2584344', 'CLEVIS', 'Clevis Assembly', '4140 Steel', 'DWG-2584344', '5365-00-151-9093'),
('N086440', 'POPPET', 'Poppet DC3500CS', '4130 Steel', 'DWG-N086440', NULL),
('12364289', 'HOLDER', 'Holder Assembly', '4140 Steel', 'DWG-12364289', NULL);