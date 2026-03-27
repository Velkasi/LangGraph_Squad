import { useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export const useAssignProgram = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      patientId,
      programId,
      assignedBy
    }: {
      patientId: string;
      programId: string;
      assignedBy: string;
    }) => {
      const { data, error } = await supabase
        .from('patient_programs')
        .insert({
          patient_id: patientId,
          program_id: programId,
          assigned_by: assignedBy,
          assigned_at: new Date().toISOString(),
          mode: 'manual'
        });
      
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-programs'] });
    },
  });
};