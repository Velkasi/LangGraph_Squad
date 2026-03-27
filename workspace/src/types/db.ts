export type User = {
  id: string;
  email: string;
  role: 'admin' | 'practitioner' | 'patient';
  organization_id: string;
};

export type Organization = {
  id: string;
  name: string;
};

export type Practitioner = {
  id: string;
  user_id: string;
  organization_id: string;
  specialty: string;
};

export type Patient = {
  id: string;
  user_id: string;
  practitioner_id: string;
  organization_id: string;
};

export type Pathology = {
  id: string;
  name: string;
  description: string;
  organization_id: string;
};

export type Program = {
  id: string;
  pathology_id: string;
  title: string;
  description: string;
  organization_id: string;
};

export type Video = {
  id: string;
  source_type: 'supabase' | 'youtube' | 'vimeo';
  source_ref: string;
  title: string;
  duration_seconds: number;
  organization_id: string;
};

export type ProgramVideo = {
  program_id: string;
  video_id: string;
  order_index: number;
};

export type PatientProgram = {
  patient_id: string;
  program_id: string;
  assigned_by: string;
  assigned_at: string;
  mode: 'manual' | 'auto';
};

export type VideoProgress = {
  patient_id: string;
  video_id: string;
  last_position_seconds: number;
  completed: boolean;
  watched_at: string;
};