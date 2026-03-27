import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export const usePatientPrograms = (patientId: string) => {
  return useQuery({
    queryKey: ['patient-programs', patientId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('patient_programs')
        .select(`
          id,
          program:programs!inner(
            id,
            title,
            description,
            pathology:pathologies!inner(name)
          ),
          assigned_at,
          mode
        `)
        .eq('patient_id', patientId)
        .order('assigned_at', { ascending: false });
      
      if (error) throw error;
      return data;
    },
    enabled: !!patientId,
  });
};