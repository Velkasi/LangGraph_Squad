-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create organizations table
CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create users table with role and organization_id
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  auth_uid UUID NOT NULL UNIQUE,
  email TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'practitioner', 'patient')),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create practitioners table
CREATE TABLE IF NOT EXISTS practitioners (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  specialty TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create patients table
CREATE TABLE IF NOT EXISTS patients (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  practitioner_id UUID NOT NULL REFERENCES practitioners(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create pathologies table
CREATE TABLE IF NOT EXISTS pathologies (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create programs table
CREATE TABLE IF NOT EXISTS programs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  pathology_id UUID NOT NULL REFERENCES pathologies(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create videos table
CREATE TABLE IF NOT EXISTS videos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('supabase', 'youtube', 'vimeo')),
  source_ref TEXT NOT NULL,
  title TEXT NOT NULL,
  duration_seconds INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create program_videos table (join table)
CREATE TABLE IF NOT EXISTS program_videos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  order_index INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create patient_programs table
CREATE TABLE IF NOT EXISTS patient_programs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
  assigned_by UUID NOT NULL REFERENCES practitioners(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ DEFAULT NOW(),
  mode TEXT NOT NULL CHECK (mode IN ('manual', 'auto')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create video_progress table
CREATE TABLE IF NOT EXISTS video_progress (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  last_position_seconds INTEGER DEFAULT 0,
  completed BOOLEAN DEFAULT FALSE,
  watched_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE practitioners ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE pathologies ENABLE ROW LEVEL SECURITY;
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE program_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_progress ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Organizations: Users can access their own organization
CREATE POLICY "Users can access own organization"
  ON organizations FOR SELECT
  USING (id = (auth.jwt()->>'org_id')::uuid);

-- Users: Can only access users from their organization
CREATE POLICY "Users can access own org users"
  ON users FOR SELECT
  USING (organization_id = (auth.jwt()->>'org_id')::uuid);

-- Practitioners: Can access practitioners from their organization
CREATE POLICY "Practitioners access own org practitioners"
  ON practitioners FOR SELECT
  USING (organization_id = (auth.jwt()->>'org_id')::uuid);

-- Patients: Can access patients from their organization
-- Practitioners can access patients assigned to them
-- Patients can access their own data
CREATE POLICY "Access patients by organization"
  ON patients FOR SELECT
  USING (organization_id = (auth.jwt()->>'org_id')::uuid);

-- Pathologies: Can access pathologies from their organization
CREATE POLICY "Access pathologies by organization"
  ON pathologies FOR SELECT
  USING (organization_id = (auth.jwt()->>'org_id')::uuid);

-- Programs: Can access programs from their organization
CREATE POLICY "Access programs by organization"
  ON programs FOR SELECT
  USING (organization_id = (auth.jwt()->>'org_id')::uuid);

-- Videos: Can access videos from their organization
CREATE POLICY "Access videos by organization"
  ON videos FOR SELECT
  USING (organization_id = (auth.jwt()->>'org_id')::uuid);

-- Program videos: Can access program_videos from their organization's programs
CREATE POLICY "Access program_videos by organization"
  ON program_videos FOR SELECT
  USING (
    program_id IN (
      SELECT id FROM programs WHERE organization_id = (auth.jwt()->>'org_id')::uuid
    )
  );

-- Patient programs: Can access patient_programs from their organization
CREATE POLICY "Access patient_programs by organization"
  ON patient_programs FOR SELECT
  USING (
    patient_id IN (
      SELECT id FROM patients WHERE organization_id = (auth.jwt()->>'org_id')::uuid
    )
  );

-- Video progress: Can access video_progress from their organization's patients
CREATE POLICY "Access video_progress by organization"
  ON video_progress FOR SELECT
  USING (
    patient_id IN (
      SELECT id FROM patients WHERE organization_id = (auth.jwt()->>'org_id')::uuid
    )
  );