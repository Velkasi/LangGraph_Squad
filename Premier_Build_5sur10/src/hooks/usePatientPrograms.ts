import { useQuery } from '@tanstack/react-query';
import { supabase } from '../lib/supabase';

export interface PatientProgram {
  id: string;
  patient_id: string;
  program_id: string;
  assigned_by: string;
  assigned_at: string;
  mode: 'manual' | 'auto';
  program: {
    id: string;
    title: string;
    description: string;
    pathology_id: string;
  };
}

export const usePatientPrograms = (patientId: string) => {
  return useQuery<PatientProgram[], Error>({
    queryKey: ['patientPrograms', patientId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('patient_programs')
        .select(`
          id,
          patient_id,
          program_id,
          assigned_by,
          assigned_at,
          mode,
          program:programs(id, title, description, pathology_id)
        `)
        .eq('patient_id', patientId);
      
      if (error) throw error;
      
      return data;
    },
    enabled: !!patientId,
  });
};