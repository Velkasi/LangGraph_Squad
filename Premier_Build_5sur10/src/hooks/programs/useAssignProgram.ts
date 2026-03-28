import { useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import type { Database } from '@/types/db';

type AssignProgramData = {
  patient_id: string;
  program_id: string;
  assigned_by: string;
};

export function useAssignProgram() {
  const queryClient = useQueryClient();

  return useMutation<
    Database['public']['Tables']['patient_programs']['Row'],
    Error,
    AssignProgramData
  >({
    mutationFn: async ({ patient_id, program_id, assigned_by }) => {
      const { data, error } = await supabase
        .from('patient_programs')
        .insert({
          patient_id,
          program_id,
          assigned_by,
          assigned_at: new Date().toISOString(),
          mode: 'manual',
        })
        .select()
        .single();

      if (error) {
        console.error('Error assigning program:', error);
        throw error;
      }

      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-programs'] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
    },
  });
}