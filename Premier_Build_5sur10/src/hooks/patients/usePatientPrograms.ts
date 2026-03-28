import { useQuery } from '@tanstack/react-query';
import { supabase } from '../../lib/supabase';

export const usePatientPrograms = (patientId: string) => {
  return useQuery({
    queryKey: ['patientPrograms', patientId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('patient_programs')
        .select(`
          id,
          assigned_at,
          mode,
          programs (id, title, description, pathology_id)
        `)
        .eq('patient_id', patientId)
        .order('assigned_at', { ascending: false });
      
      if (error) {
        throw error;
      }
      
      return data;
    },
    enabled: !!patientId,
  });
};