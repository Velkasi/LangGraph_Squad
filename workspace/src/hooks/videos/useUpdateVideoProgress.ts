import { useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export const useUpdateVideoProgress = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      patientId,
      videoId,
      lastPositionSeconds,
      completed
    }: {
      patientId: string;
      videoId: string;
      lastPositionSeconds: number;
      completed: boolean;
    }) => {
      const { data, error } = await supabase
        .from('video_progress')
        .upsert({
          patient_id: patientId,
          video_id: videoId,
          last_position_seconds: lastPositionSeconds,
          completed,
          watched_at: new Date().toISOString()
        }, {
          onConflict: 'patient_id,video_id'
        });
      
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-progress'] });
    },
  });
};