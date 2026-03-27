export interface Organization {
  id: string;
  name: string;
  created_at: string;
}

export interface User {
  id: string;
  auth_uid: string;
  email: string;
  role: 'admin' | 'practitioner' | 'patient';
  organization_id: string;
  created_at: string;
}

export interface Practitioner {
  id: string;
  user_id: string;
  organization_id: string;
  specialty: string | null;
  created_at: string;
}

export interface Patient {
  id: string;
  user_id: string;
  practitioner_id: string;
  organization_id: string;
  created_at: string;
}

export interface Pathology {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Program {
  id: string;
  organization_id: string;
  pathology_id: string;
  title: string;
  description: string | null;
  created_at: string;
}

export interface Video {
  id: string;
  organization_id: string;
  source_type: 'supabase' | 'youtube' | 'vimeo';
  source_ref: string;
  title: string;
  duration_seconds: number | null;
  created_at: string;
}

export interface ProgramVideo {
  id: string;
  program_id: string;
  video_id: string;
  order_index: number;
  created_at: string;
}

export interface PatientProgram {
  id: string;
  patient_id: string;
  program_id: string;
  assigned_by: string;
  assigned_at: string;
  mode: 'manual' | 'auto';
  created_at: string;
}

export interface VideoProgress {
  id: string;
  patient_id: string;
  video_id: string;
  last_position_seconds: number;
  completed: boolean;
  watched_at: string;
  created_at: string;
}