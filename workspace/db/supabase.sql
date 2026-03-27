-- Table: organizations
CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- RLS Policies for organizations
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
-- Only admins can manage organizations (assumed)
CREATE POLICY "Admin can manage organizations" ON organizations
  FOR ALL USING (
    (auth.jwt() ->> 'role')::TEXT = 'admin'
  );


-- Table: users
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE,
  role TEXT CHECK (role IN ('admin', 'practitioner', 'patient')) NOT NULL,
  auth_uid TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- RLS Policies for users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own org users" ON users
  FOR SELECT USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Admins can manage users" ON users
  FOR INSERT WITH CHECK (
    (auth.jwt() ->> 'role')::TEXT = 'admin' AND
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Users cannot modify users" ON users
  FOR UPDATE USING (FALSE);
CREATE POLICY "Users cannot delete users" ON users
  FOR DELETE USING (FALSE);


-- Table: practitioners
CREATE TABLE IF NOT EXISTS practitioners (
  id UUID PRIMARY KEY DEFAULT gen_random_uid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  specialty TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- RLS Policies for practitioners
ALTER TABLE practitioners ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Practitioners and admins can view" ON practitioners
  FOR SELECT USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Admins can insert practitioners" ON practitioners
  FOR INSERT WITH CHECK (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Practitioners cannot modify practitioners" ON practitioners
  FOR UPDATE USING (FALSE);
CREATE POLICY "Practitioners cannot delete practitioners" ON practitioners
  FOR DELETE USING (FALSE);


-- Table: patients
CREATE TABLE IF NOT EXISTS patients (
  id UUID PRIMARY KEY DEFAULT gen_random_uid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  practitioner_id UUID NOT NULL REFERENCES practitioners(id) ON DELETE RESTRICT,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- RLS Policies for patients
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Patients can view self" ON patients
  FOR SELECT USING (
    user_id = (auth.jwt() ->> 'sub')::UUID
  );
CREATE POLICY "Practitioners can view patients" ON patients
  FOR SELECT USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Admins can manage patients" ON patients
  FOR ALL USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );


-- Table: pathologies
CREATE TABLE IF NOT EXISTS pathologies (
  id UUID PRIMARY KEY DEFAULT gen_random_uid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- RLS Policies for pathologies
ALTER TABLE pathologies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view pathologies" ON pathologies
  FOR SELECT USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Admins and practitioners can create pathologies" ON pathologies
  FOR INSERT WITH CHECK (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Admins and practitioners can update pathologies" ON pathologies
  FOR UPDATE USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Admins can delete pathologies" ON pathologies
  FOR DELETE USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );


-- Table: programs
CREATE TABLE IF NOT EXISTS programs (
  id UUID PRIMARY KEY DEFAULT gen_random_uid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  pathology_id UUID NOT NULL REFERENCES pathologies(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- RLS Policies for programs
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view programs" ON programs
  FOR SELECT USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Admins and practitioners can manage programs" ON programs
  FOR ALL USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );


-- Table: videos
CREATE TABLE IF NOT EXISTS videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  source_type TEXT CHECK (source_type IN ('supabase', 'youtube', 'vimeo')) NOT NULL,
  source_ref TEXT NOT NULL,
  title TEXT NOT NULL,
  duration_seconds INTEGER NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- RLS Policies for videos
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view videos" ON videos
  FOR SELECT USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );
CREATE POLICY "Admins and practitioners can manage videos" ON videos
  FOR ALL USING (
    organization_id = (auth.jwt() ->> 'org_id')::UUID
  );


-- Table: program_videos
CREATE TABLE IF NOT EXISTS program_videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uid(),
  program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  order_index INTEGER NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL,
  UNIQUE(program_id, video_id)
);

-- RLS Policies for program_videos
ALTER TABLE program_videos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view program_videos" ON program_videos
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM programs p WHERE p.id = program_id AND p.organization_id = (auth.jwt() ->> 'org_id')::UUID
    )
  );
CREATE POLICY "Admins and practitioners can manage program_videos" ON program_videos
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM programs p WHERE p.id = program_id AND p.organization_id = (auth.jwt() ->> 'org_id')::UUID
    )
  );


-- Table: patient_programs
CREATE TABLE IF NOT EXISTS patient_programs (
  id UUID PRIMARY KEY DEFAULT gen_random_uid(),
  patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
  assigned_by UUID NOT NULL REFERENCES practitioners(id) ON DELETE RESTRICT,
  assigned_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL,
  mode TEXT CHECK (mode IN ('manual', 'auto')) NOT NULL,
  UNIQUE(patient_id, program_id)
);

-- RLS Policies for patient_programs
ALTER TABLE patient_programs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Patients can view own program assignments" ON patient_programs
  FOR SELECT USING (
    patient_id IN (SELECT id FROM patients WHERE user_id = (auth.jwt() ->> 'sub')::UUID)
  );
CREATE POLICY "Practitioners can view assigned programs" ON patient_programs
  FOR SELECT USING (
    assigned_by = (auth.jwt() ->> 'sub')::UUID
  );
CREATE POLICY "Admins and practitioners can assign programs" ON patient_programs
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM patients p WHERE p.id = patient_id AND p.organization_id = (auth.jwt() ->> 'org_id')::UUID
    )
  );


-- Table: video_progress
CREATE TABLE IF NOT EXISTS video_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uid(),
  patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  last_position_seconds INTEGER NOT NULL,
  completed BOOLEAN DEFAULT FALSE NOT NULL,
  watched_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL,
  UNIQUE(patient_id, video_id)
);

-- RLS Policies for video_progress
ALTER TABLE video_progress ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Patients can view own progress" ON video_progress
  FOR ALL USING (
    patient_id IN (SELECT id FROM patients WHERE user_id = (auth.jwt() ->> 'sub')::UUID)
  );
CREATE POLICY "Practitioners can view patient progress" ON video_progress
  FOR SELECT USING (
    patient_id IN (
      SELECT p.id FROM patients p
      JOIN practitioners pr ON p.practitioner_id = pr.id
      WHERE pr.organization_id = (auth.jwt() ->> 'org_id')::UUID
    )
  );