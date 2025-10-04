-- Payment Processing Tables for Bondah Dating API
-- Execute this script in pgAdmin to create payment processing tables

-- Create PaymentMethod table
CREATE TABLE IF NOT EXISTS dating_paymentmethod (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    processing_fee_percentage DECIMAL(5,2) DEFAULT 0.00,
    min_amount DECIMAL(10,2) DEFAULT 1.00,
    max_amount DECIMAL(10,2) DEFAULT 10000.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for PaymentMethod
CREATE INDEX IF NOT EXISTS dating_paym_is_acti_4635f1_idx ON dating_paymentmethod (is_active);

-- Create PaymentTransaction table
CREATE TABLE IF NOT EXISTS dating_paymenttransaction (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL,
    payment_method_id INTEGER NOT NULL REFERENCES dating_paymentmethod(id) ON DELETE CASCADE,
    amount_usd DECIMAL(10,2) NOT NULL,
    processing_fee DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'pending',
    provider VARCHAR(50),
    provider_transaction_id VARCHAR(255),
    provider_response JSONB,
    subscription_id INTEGER REFERENCES dating_usersubscription(id) ON DELETE SET NULL,
    bondcoin_transaction_id INTEGER REFERENCES dating_bondcointransaction(id) ON DELETE SET NULL,
    description VARCHAR(255) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for PaymentTransaction
CREATE INDEX IF NOT EXISTS dating_paym_user_id_bbfd7b_idx ON dating_paymenttransaction (user_id, status);
CREATE INDEX IF NOT EXISTS dating_paym_provide_9057a7_idx ON dating_paymenttransaction (provider_transaction_id);
CREATE INDEX IF NOT EXISTS dating_paym_status_e09868_idx ON dating_paymenttransaction (status, created_at);

-- Create PaymentWebhook table
CREATE TABLE IF NOT EXISTS dating_paymentwebhook (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_id VARCHAR(255) NOT NULL,
    transaction_id INTEGER REFERENCES dating_paymenttransaction(id) ON DELETE CASCADE,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processing_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for PaymentWebhook
CREATE INDEX IF NOT EXISTS dating_paym_provide_e504a7_idx ON dating_paymentwebhook (provider, event_type);
CREATE INDEX IF NOT EXISTS dating_paym_process_8ef90a_idx ON dating_paymentwebhook (processed, created_at);

-- Create unique constraint for PaymentWebhook
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'dating_paymentwebhook_provider_event_id_unique'
    ) THEN
        ALTER TABLE dating_paymentwebhook ADD CONSTRAINT dating_paymentwebhook_provider_event_id_unique UNIQUE (provider, event_id);
    END IF;
END $$;

-- Insert default payment methods
INSERT INTO dating_paymentmethod (name, display_name, description, icon_url, is_active, processing_fee_percentage, min_amount, max_amount) VALUES
('credit_card', 'Credit Card', 'Pay with your credit card', 'https://example.com/icons/credit-card.png', TRUE, 2.9, 1.00, 10000.00),
('debit_card', 'Debit Card', 'Pay with your debit card', 'https://example.com/icons/debit-card.png', TRUE, 2.5, 1.00, 5000.00),
('paypal', 'PayPal', 'Pay with PayPal', 'https://example.com/icons/paypal.png', TRUE, 3.4, 1.00, 10000.00),
('apple_pay', 'Apple Pay', 'Pay with Apple Pay', 'https://example.com/icons/apple-pay.png', TRUE, 2.9, 1.00, 10000.00),
('google_pay', 'Google Pay', 'Pay with Google Pay', 'https://example.com/icons/google-pay.png', TRUE, 2.9, 1.00, 10000.00),
('bank_transfer', 'Bank Transfer', 'Direct bank transfer', 'https://example.com/icons/bank-transfer.png', TRUE, 0.0, 10.00, 50000.00),
('crypto', 'Cryptocurrency', 'Pay with cryptocurrency', 'https://example.com/icons/crypto.png', TRUE, 1.0, 5.00, 100000.00)
ON CONFLICT (name) DO NOTHING;

-- Add constraints for PaymentTransaction
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_transaction_type'
    ) THEN
        ALTER TABLE dating_paymenttransaction ADD CONSTRAINT check_transaction_type 
            CHECK (transaction_type IN ('subscription', 'bondcoin_purchase', 'refund'));
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_status'
    ) THEN
        ALTER TABLE dating_paymenttransaction ADD CONSTRAINT check_status 
            CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded'));
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_currency'
    ) THEN
        ALTER TABLE dating_paymenttransaction ADD CONSTRAINT check_currency 
            CHECK (currency IN ('USD', 'EUR', 'GBP', 'CAD', 'AUD'));
    END IF;
END $$;

-- Add constraints for PaymentWebhook
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_provider'
    ) THEN
        ALTER TABLE dating_paymentwebhook ADD CONSTRAINT check_provider 
            CHECK (provider IN ('stripe', 'paypal', 'square', 'razorpay', 'flutterwave'));
    END IF;
END $$;

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
DROP TRIGGER IF EXISTS update_dating_paymentmethod_updated_at ON dating_paymentmethod;
CREATE TRIGGER update_dating_paymentmethod_updated_at
    BEFORE UPDATE ON dating_paymentmethod
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_dating_paymenttransaction_updated_at ON dating_paymenttransaction;
CREATE TRIGGER update_dating_paymenttransaction_updated_at
    BEFORE UPDATE ON dating_paymenttransaction
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE dating_paymentmethod IS 'Available payment methods for users';
COMMENT ON TABLE dating_paymenttransaction IS 'Payment transactions for subscriptions and Bondcoin purchases';
COMMENT ON TABLE dating_paymentwebhook IS 'Webhook events from payment providers';

COMMENT ON COLUMN dating_paymentmethod.processing_fee_percentage IS 'Processing fee percentage for this payment method';
COMMENT ON COLUMN dating_paymentmethod.min_amount IS 'Minimum transaction amount in USD';
COMMENT ON COLUMN dating_paymentmethod.max_amount IS 'Maximum transaction amount in USD';

COMMENT ON COLUMN dating_paymenttransaction.amount_usd IS 'Transaction amount in USD before fees';
COMMENT ON COLUMN dating_paymenttransaction.processing_fee IS 'Processing fee amount in USD';
COMMENT ON COLUMN dating_paymenttransaction.total_amount IS 'Total amount including processing fees';
COMMENT ON COLUMN dating_paymenttransaction.provider_transaction_id IS 'External payment provider transaction ID';
COMMENT ON COLUMN dating_paymenttransaction.provider_response IS 'Full response data from payment provider';

COMMENT ON COLUMN dating_paymentwebhook.event_id IS 'Unique event ID from payment provider';
COMMENT ON COLUMN dating_paymentwebhook.payload IS 'Complete webhook payload from payment provider';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON dating_paymentmethod TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON dating_paymenttransaction TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON dating_paymentwebhook TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE dating_paymentmethod_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE dating_paymenttransaction_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE dating_paymentwebhook_id_seq TO your_app_user;

-- Success message
SELECT 'Payment processing tables created successfully!' as status;
