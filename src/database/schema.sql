-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    user_type VARCHAR(50) NOT NULL DEFAULT 'collector',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT valid_user_type CHECK (user_type IN ('collector', 'dealer', 'developer'))
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    plan_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    start_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_plan_type CHECK (plan_type IN ('free', 'pro')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'cancelled', 'expired'))
);

-- Collections table
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Cards table
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID REFERENCES collections(id),
    player_name VARCHAR(255) NOT NULL,
    set_name VARCHAR(255),
    year INTEGER,
    card_number VARCHAR(50),
    parallel VARCHAR(255),
    manufacturer VARCHAR(255),
    features TEXT,
    graded BOOLEAN DEFAULT FALSE,
    grade VARCHAR(50),
    grading_company VARCHAR(50),
    cert_number VARCHAR(255),
    image_url TEXT,
    price_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Card images table
CREATE TABLE card_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_id UUID REFERENCES cards(id),
    image_url TEXT NOT NULL,
    image_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_image_type CHECK (image_type IN ('front', 'back', 'detail'))
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_collections_user_id ON collections(user_id);
CREATE INDEX idx_cards_collection_id ON cards(collection_id);
CREATE INDEX idx_cards_player_name ON cards(player_name);
CREATE INDEX idx_cards_set_name ON cards(set_name);
CREATE INDEX idx_cards_year ON cards(year);
CREATE INDEX idx_card_images_card_id ON card_images(card_id); 