export interface Organization {
  id: string;
  name: string;
  email: string;
  password: string;
}

export interface User {
  id: number;
  organization_id: string;
  email: string;
  password: string;
  role: 'admin' | 'practitioner' | 'patient';
}

export interface Practitioner {
  id: number;
  organization_id: string;
  user_id: number;
  specialty?: string;
}

export interface Patient {
  id: number;
  organization_id: string;
  practitioner_id: number;
  user_id: number;
}

export interface Pathology {
  id: number;
  organization_id: string;
  name: string;
  description?: string;
}

export interface Program {
  id: number;
  organization_id: string;
  pathology_id: number;
  title: string;
  description?: string;
}

export interface Video {
  id: number;
  organization_id: string;
  source_type: 'supabase' | 'youtube' | 'vimeo';
  source_ref: string;
  title: string;
  duration_seconds: number;
}

export interface ProgramVideo {
  id: number;
  program_id: number;
  video_id: number;
  order_index: number;
}

export interface PatientProgram {
  id: number;
  patient_id: number;
  program_id: number;
  assigned_by: number;
  assigned_at: string;
  mode: 'manual' | 'auto';
}

export interface VideoProgress {
  id: number;
  patient_id: number;
  video_id: number;
  last_position_seconds: number;
  completed: boolean;
  watched_at: string;
}