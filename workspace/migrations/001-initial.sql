-- Multi-tenant SaaS migration file
-- Created in strict FK order per architecture

-- 1. organizations
CREATE TABLE organizations (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. users
CREATE TABLE users (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  role TEXT NOT NULL CHECK (role IN ('admin', 'practitioner', 'patient')),
  auth_uid UUID REFERENCES auth.users(id),
  FOREIGN KEY (org_id) REFERENCES organizations(id)
);

-- 3. practitioners
CREATE TABLE practitioners (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  org_id UUID NOT NULL REFERENCES organizations(id),
  specialty TEXT NOT NULL
);

-- 4. patients
CREATE TABLE patients (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  practitioner_id UUID NOT NULL REFERENCES practitioners(id),
  user_id UUID NOT NULL REFERENCES users(id)
);

-- 5. pathologies
CREATE TABLE pathologies (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  name TEXT NOT NULL,
  description TEXT,
  is_global BOOLEAN DEFAULT false
);

-- 6. programs
CREATE TABLE programs (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  pathology_id UUID NOT NULL REFERENCES pathologies(id),
  title TEXT NOT NULL,
  description TEXT
);

-- 7. videos
CREATE TABLE videos (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  source_type TEXT NOT NULL CHECK (source_type IN ('supabase', 'youtube', 'vimeo')),
  source_ref TEXT NOT NULL,
  title TEXT NOT NULL,
  duration_seconds INTEGER NOT NULL
);

-- 8. program_videos
CREATE TABLE program_videos (
  program_id UUID NOT NULL REFERENCES programs(id),
  video_id UUID NOT NULL REFERENCES videos(id),
  order_index INTEGER NOT NULL
);

-- 9. patient_programs
CREATE TABLE patient_programs (
  patient_id UUID NOT NULL REFERENCES patients(id),
  program_id UUID NOT NULL REFERENCES programs(id),
  assigned_by UUID NOT NULL REFERENCES practitioners(id),
  mode TEXT NOT NULL CHECK (mode IN ('manual', 'auto'))
);

-- 10. video_progress
CREATE TABLE video_progress (
  patient_id UUID NOT NULL REFERENCES patients(id),
  video_id UUID NOT NULL REFERENCES videos(id),
  last_position_seconds INTEGER NOT NULL DEFAULT 0,
  completed BOOLEAN NOT NULL DEFAULT false,
  watched_at TIMESTAMPTZ
);

-- Recommended indexes
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_patients_practitioner_id ON patients(practitioner_id);
CREATE INDEX idx_program_videos_program_id ON program_videos(program_id);
CREATE INDEX idx_video_progress_patient_video ON video_progress(patient_id, video_id);