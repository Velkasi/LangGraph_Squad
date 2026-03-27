export type Organization = {
  id: string;
  name: string;
  created_at: string;
};

export type User = {
  id: string;
  email: string;
  role: 'admin' | 'practitioner' | 'patient';
  organization_id: string;
  auth_uid: string;
  created_at: string;
};

export type Practitioner = {
  id: string;
  user_id: string;
  organization_id: string;
  specialty: string;
  created_at: string;
};

export type Patient = {
  id: string;
  user_id: string;
  organization_id: string;
  practitioner_id: string | null;
  created_at: string;
};

export type Pathology = {
  id: string;
  name: string;
  description: string;
  organization_id: string;
  created_at: string;
};

export type Program = {
  id: string;
  title: string;
  description: string;
  pathology_id: string;
  organization_id: string;
  created_at: string;
};

export type Video = {
  id: string;
  title: string;
  duration_seconds: number;
  source_type: 'supabase' | 'youtube' | 'vimeo';
  source_ref: string;
  organization_id: string;
  created_at: string;
};

export type ProgramVideo = {
  id: string;
  program_id: string;
  video_id: string;
  order_index: number;
  created_at: string;
};

export type PatientProgram = {
  id: string;
  patient_id: string;
  program_id: string;
  assigned_by: string;
  assigned_at: string;
  mode: 'manual' | 'auto';
};

export type VideoProgress = {
  id: string;
  patient_id: string;
  video_id: string;
  last_position_seconds: number;
  completed: boolean;
  watched_at: string;
};